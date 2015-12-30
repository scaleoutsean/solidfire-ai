#!/usr/bin/python

""" this program will create a number of bootable volumes from
    images stored in Glance. It will not clone the volumes, but 
    continue to use whatever mechanism is configured to get the images 
    from Glance, including any image caching configured.
"""

import os
from optparse import OptionParser
import random
import sys
import time

from cinderclient import client as cinderclient
from novaclient.v2 import client as novaclient

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

    parser.add_option('-c', '--instance-count', action='store',
                      type='int',
                      default=2,
                      dest='instance_count',
                      help='Number of instances to boot (default = 2).')

    parser.add_option('-s', '--size', action='store',
                      type='string',
                      default='10',
                      dest='volume_size',
                      help='Size of volume to create for template')

    parser.add_option('-i', '--image-id', action='store',
                      type='string',
                      dest='image_id',
                      help='Imaged ID to use if creating the template (not specifying a Template list)')

    parser.add_option('-n', '--name', action='store',
                      type='string',
                      default='verification',
                      dest='volume_base_name',
                      help='Base name to use for new template volume ( -template will be added)')

    parser.add_option('-t', '--type', action='store',
                      type='string',
                      dest='vol_type',
                      help='Volume Type to use for new template volume (default: random vol_type)')

    (options, args) = parser.parse_args()
    return options

def init_clients():
    cc = cinderclient.Client('2', USER,
                              PASSWORD, TENANT,
                              AUTH_URL)
    nc = novaclient.Client(USER, PASSWORD,
                             TENANT, AUTH_URL,
                             service_type="compute")
    return cc, nc

def wait_for_ready(cc, volume_list):
    ready_count = 0
    error_count = 0
    error_list = []
    return_list = []
    while volume_list:
        for v in volume_list:
            status = cc.volumes.get(v.id).status
            if status == 'available':
                ready_count += 1
                return_list.append(v)
                volume_list.remove(v)
            if 'error' in status:
                error_count += 1
                volume_list.remove(v)
                error_list.append(v)
        time.sleep(1)
    print 'Avaliable: %s Error %s' % (ready_count, error_count)
    return return_list, error_list

if __name__ == '__main__':

    options = process_options()
    (cc, nc) = init_clients()

    # We'll hit some max clones at first
    # but after a few complete we should
    # limit that impact by spreading the job
    # across multiple volumes
    start_time = time.time()
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

        base_name = options.volume_base_name

        try:
            created.append(
                cc.volumes.create(options.volume_size,
                                  name='%s-%s' % (base_name, i),
                                  volume_type=options.vol_type,
                                  imageRef=options.image_id,))

        except Exception as ex:
            print "Error:%s" % ex
            pass
        counter += 1

    print 'Issued API calls to create %s volumes.' % counter
    print 'Elapsed API time was:%s seconds' % (time.time() - start_time)
    print 'Waiting for %s volumes to become "avaliable"' % len(created)
    if options.wait_for_ready == 1:
        (created, err_list) = wait_for_ready(cc, created)
        # make this highly available (i.e. fix any error volumes)
        while err_list:
            created_err = []
            for err in err_list:
                cc.volumes.delete(err.id)
                try:
                    created_err.append(
                        cc.volumes.create(options.volume_size,
                                          name='%s' % (err.name),
                                          volume_type=options.vol_type,
                                          imageRef=options.image_id,))
                except Exception as ex:
                    print "Error:%s" % ex
                    pass
            (created_err, err_list) = wait_for_ready(cc, created_err)
            for v in created_err:
                created.append(v)
    
    print 'Total time was:%s seconds' % (time.time() - start_time)

