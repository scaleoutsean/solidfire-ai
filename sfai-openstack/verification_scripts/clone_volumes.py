#!/usr/bin/python

import os
from optparse import OptionParser
import random
import sys
import time

from cinderclient import client as cinderclient
from novaclient.v1_1 import client as novaclient

USER = os.getenv('OS_USERNAME')
TENANT = os.getenv('OS_TENANT_NAME')
PASSWORD = os.getenv('OS_PASSWORD')
AUTH_URL = os.getenv('OS_AUTH_URL')

def process_options():
    config = {}
    usage = "usage: %prog [options]\nverify_setup_deployment.py."
    parser = OptionParser(usage, version='%prog 1.0')

    parser.add_option('-w', '--wait-for-ready', action='store',
                      type='int',
                      default=1,
                      dest='wait_for_ready',
                      help='Wait for volumes to become available (default = True).')

    parser.add_option('-o', '--openstack-version', action='store',
                      type='string',
                      default='havana',
                      dest='openstack_version',
                      help='Version of OpenStack havana, icehouse (default = havana).')

    parser.add_option('-c', '--instance-count', action='store',
                      type='int',
                      default=100,
                      dest='instance_count',
                      help='Number of instances to boot (default = 100).')

    parser.add_option('-s', '--size', action='store',
                      type='string',
                      default='10',
                      dest='volume_size',
                      help='Size of volume to create for template')

    # TODO: Convert to callback
    parser.add_option('-v', '--volumes', action='store',
                      type='string',
                      dest='template_list',
                      help='Comma seperated list of volume IDs to use as templates (omit to create a template).')

    parser.add_option('-i', '--image-id', action='store',
                      type='string',
                      dest='image_id',
                      help='Imaged ID to use if creating the template (not specifying a Templat list)')

    parser.add_option('-n', '--name', action='store',
                      type='string',
                      default='verfication',
                      dest='volume_base_name',
                      help='Base name to use for new template volume (ie: Template)')

    (options, args) = parser.parse_args()
    return options

def init_clients():
    cc = cinderclient.Client('1', USER,
                              PASSWORD, TENANT,
                              AUTH_URL)
    nc = novaclient.Client(USER, PASSWORD,
                             TENANT, AUTH_URL,
                             service_type="compute")
    return cc, nc

def wait_for_ready(cc, volume_list):
    ready_count = 0
    error_count = 0
    while ready_count + error_count < len(volume_list):
        for v in volume_list:
            status = cc.volumes.get(v.id).status
            if status == 'available':
                ready_count += 1
                volume_list.remove(v)
            if 'error' in status:
                error_count += 1
                volume_list.remove(v)
        time.sleep(1)

def create_template(options, cc):
    if options.image_id is None or options.volume_base_name is None:
        print ('Missing parameter to create Template, require: image-id and name')
        sys.exit(1)
    create_start = time.time()
    vref = cc.volumes.create(options.volume_size,
                             imageRef=options.image_id)
    while cc.volumes.get(vref.id).status != 'available':
        time.sleep(1)
    print "Template volume ready after %s seconds." % (time.time() - create_start)
    return vref.id

if __name__ == '__main__':

    options = process_options()
    master_vlist = []
    (cc, nc) = init_clients()
    if options.template_list is None:
        print ('No Template list provided, attempting to create a template...')
        master_vlist.append(create_template(options, cc))
    else:
       master_vlist = options.template_list.split(',')


    # We'll hit some max clones at first
    # but after a few complete we should
    # limit that impact by spreading the job
    # across multiple volumes
    start_time = time.time()
    vtype_list = cc.volume_types.list()
    counter = 0
    refresh_point = 10
    created = []
    

    for i in xrange(options.instance_count):
        if counter == refresh_point:
            created_id_list = [v.id for v in created]
            vlist = cc.volumes.list(search_opts={'status': 'available'})
            for v in vlist:
                if v.id in created_id_list:
                    master_vlist.append(v.id)
            refresh_point = refresh_point * 2

        src_id = random.choice(master_vlist)
        base_name = cc.volumes.get(src_id).display_name
        if '-' in base_name:
            base_name = base_name.split('-')[0]

        if len(vtype_list) > 0:
            vtype = random.choice(vtype_list)
        try:
            if options.openstack_version == 'icehouse':
                vtype.id = None
            created.append(
                cc.volumes.create(options.volume_size,
                                  display_name='%s-%s' % (base_name, i),
                                  source_volid=src_id,
                                  volume_type=vtype.id))
        except Exception as ex:
            print "Error:%s" % ex
            pass
        counter += 1
    print 'Issued API calls to create %s clones.' % counter
    print 'Elapsed time was:%s seconds' % (time.time() - start_time)
    if options.wait_for_ready == 1:
        wait_for_ready(cc, created)
