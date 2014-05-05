#!/usr/bin/python

import logging
import socket
import sys
import time
from contextlib import contextmanager
from optparse import OptionParser

from libs import servers
from libs import volumes

BASE_VOLUME_TYPE_ID = '651ba0a5-96ef-4550-9a4a-0c09c230237d'
@contextmanager
def _timer(mesg):
    start = time.time()
    yield
    end = time.time()
    logging.info('%s: %0.2f seconds' % (mesg, end-start))

def wait_for_vol_available(volume_id):
    counter = 0
    logging.info("Creating volume from image...")
    status = vmgr.get_volume_status(volume_id)
    while status != 'available' and counter < 600:
        time.sleep(1)
        counter += 1
        status = vmgr.get_volume_status(volume_id)
    if counter < 600 and status == 'available':
        logging.info("Downloaded image from glance in %s seconds" % counter)
        return True
    else:
        status = vmgr.get_volume_status(volume_id)
        logging.error("Faield to become ready in 600 seconds.")
        logging.error("Status after the 600 second timeout was: %s" % status)
        return False

def process_options():
    config = {}
    usage = "usage: %prog [options]\nLaunch OS worker."
    parser = OptionParser(usage, version='%prog 1.0')

    parser.add_option('-V', '--verbose', action='store_true',
                      default=False,
                      dest='verbose',
                      help='Enable verbose logging.')

    parser.add_option('-n', '--numinstances', action='store',
                      type='int',
                      default=1,
                      dest='num_instances',
                      help='Number of instances to create using '
                           'cloned volumes. (Defaults to 1)')

    parser.add_option('-v', '--volid', action='store',
                      type='string',
                      default=None,
                      dest='master_vol_id',
                      help='Cinder volume id to use as instance template')

    parser.add_option('-f', '--flavor', action='store',
                      type='string',
                      default='3',
                      dest='instance_flavor',
                      help='Flavor to use when building instance.')

    parser.add_option('-N', '--worker-name', action='store',
                      type='string',
                      default='noname',
                      dest='worker_name',
                      help='Name to assign to this worker.')

    (options, args) = parser.parse_args()
    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)

    return options

if __name__ == '__main__':

    if len(sys.argv) == 1:
        sys.argv.append('-h')

    logging.basicConfig(level=logging.INFO,
                        filename='./createvols.log',
                        filemode='w')
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    logging.getLogger('').addHandler(console)

    options = process_options()
    vmgr = volumes.Volumes()
    smgr = servers.Servers()

    master_vref = vmgr.get_vref(options.master_vol_id)

    counter = 0
    clone_list = []
    while counter < options.num_instances:
        clone_list.append(vmgr.create(master_vref.size,
                          display_name="%s-%s" % (options.worker_name, counter),
                          source_volid=master_vref.id, volume_type=BASE_VOLUME_TYPE_ID))
        time.sleep(1)
        counter += 1

    vlist = []
    for v in clone_list:
        vlist.append({'vref': v, 'status': 'pending'})

    pending_count = len(vlist)
    with _timer('Time for ready of %s volume clones' % options.num_instances):
        while pending_count > 0:
            for v in vlist:
                existing_status = v['status']
                if existing_status == 'available' or existing_status == 'error':
                    pass
                else:
                    vobj = vmgr.get_vref(v['vref'].id)
                    if vobj.status == 'creating':
                        pass
                    else:
                        pending_count -= 1
                        v['status'] = vobj.status

    #boot-em up
    instance_list = []
    counter=0
    for v in vlist:
        instance_list.append(
            smgr.create_server(options.instance_flavor,
                               v['vref'].id,
                               '%s-%s-%s' % (options.worker_name,
                                             socket.gethostname(),
                                             counter)))
        time.sleep(1)
        counter += 1

    pending_count = len(vlist)
    with _timer('Time for ready of %s instance boots' % options.num_instances):
        while pending_count > 0:
            for i in instance_list:
                existing_status = i.status
                if existing_status.lower() == 'active' or existing_status.lower() == 'error':
                    logging.info('pass')
                    pass
                else:
                    iobj = smgr.get_iref(i.id)
                    if iobj.status.lower() == 'error' or iobj.status.lower() == 'active':
                        pending_count -= 1
                        logging.info('decrement... status: %s' % iobj.status)
                        i = iobj
