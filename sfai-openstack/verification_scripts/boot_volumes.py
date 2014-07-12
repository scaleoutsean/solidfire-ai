#!/usr/bin/python

import logging
import os
from optparse import OptionParser
import random
import time

from cinderclient import client as cinderclient
from novaclient.v1_1 import client as novaclient

USER = os.getenv('OS_USERNAME')
TENANT = os.getenv('OS_TENANT_NAME')
PASSWORD = os.getenv('OS_PASSWORD')
AUTH_URL = os.getenv('OS_AUTH_URL')

def process_options():
    config = {}
    usage = "usage: %prog [options]\nboot_volumes.py."
    parser = OptionParser(usage, version='%prog 1.0')

    parser.add_option('-c', '--instance-count', action='store',
                      type='int',
                      default=100,
                      dest='instance_count',
                      help='Number of instances to boot (default = 100).')

    parser.add_option('-n', '--name', action='store',
                      type='string',
                      dest='base_name',
                      help='Base name to use, this is the base name '
                           'name for the volume-templates you want to boot. ' 
                            '(Remember to include delimeter \'-\')')

    # Other tests use random flavors, but this one we MUST specify flavor
    parser.add_option('-f', '--flavors', action='store',
                      type='string',
                      dest='flavor_list',
                      help='Comma seperated list of flavors to choose from') 

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

if __name__ == '__main__':

    start_time = time.time()
    options = process_options()
    (cc, nc) = init_clients()
    counter = 0
    flavor_list = options.flavor_list.split(',')

    # Only ask for a fresh list of ready volumes when we need to
    # ie don't grab an update every iteration, no need to and it
    # introduces significant overhead
    ready_vlist =\
        [v for v in cc.volumes.list(search_opts={'status': 'available'}) if options.base_name in v.display_name]
    instance_start_time = time.time()
    for i in xrange(options.instance_count):
        if len(ready_vlist) < 1 :
            print('No ready volumes to boot, wait and rescan...')
            ready_vlist =\
                [v for v in cc.volumes.list(search_opts={'status': 'available'}) if options.base_name in v.display_name]
            counter = 0
            continue
        src_vol = random.choice(ready_vlist)
        create_kwargs = {}
        bdm = {'vda': src_vol.id + ':::0'}
        create_kwargs['block_device_mapping']  = bdm
        flavor_id = random.choice(flavor_list)
        try:
            nc.servers.create(src_vol.display_name, None, flavor_id,  **create_kwargs)
            ready_vlist.remove(src_vol)
        except Exception as ex:
            print 'Caught exception booting instance: %s' % ex
            pass
        counter += 1
        if counter % 20 == 0:
            time.sleep(10)
    print('Boot process completed in %s secs (elapsed test time  %s secs)' %
          (time.time() - instance_start_time, time.time() - start_time))
    # Now we just have to wait for the instances to become ACTIVE
    done_count = 0
    while done_count < options.instance_count:
        active_list = nc.servers.list(search_opts={'status': 'ACTIVE'})
        error_list = nc.servers.list(search_opts={'status': 'ERROR'})
        done_count = len(active_list) + len(error_list)
        print "    Active/Ready Instances: %s" % len(active_list)
        print "    Error/Failed Instances: %s\n" % len(error_list)
        time.sleep(5)
        if ((time.time() - start_time) / 60) > 30:
            break
    print "    Active/Ready Instances: %s" % len(active_list)
    print "    Error/Failed Instances: %s\n" % len(error_list)
    print "completion time: %s minutes" % ((time.time() - start_time) / 60)

