#!/usr/bin/python

import logging
import os
from optparse import OptionParser
import random
import time

from cinderclient import client as cinderclient
from novaclient.v2 import client as novaclient

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
                      default=2,
                      dest='instance_count',
                      help='Number of instances to boot (default = 2).')

    parser.add_option('-n', '--name', action='store',
                      type='string',
                      default='verification',
                      dest='base_name',
                      help='Base name to use, this is the base name '
                           'name for the volume-templates you want to boot. ' 
                           'you probably dont want to run the template itself'
                           '(default: verification)')

    # Other tests use random flavors, but this one we MUST specify flavor
    parser.add_option('-f', '--flavors', action='store',
                      type='string',
                      dest='flavor_list',
                      help='Comma seperated list of flavors to choose from') 

    parser.add_option('-t', '--template', action='store',
                      type='string',
                      default='-template',
                      dest='template',
                      help='The suffix to designate the template (default: -template)')

    parser.add_option('-e', '--network', action='store',
                      type='string',
                      dest='net_UUID',
                      help='The UUID of the network to attach the instances to')

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

if __name__ == '__main__':

    start_time = time.time()
    options = process_options()
    (cc, nc) = init_clients()
    counter = 0
    flavor_list = options.flavor_list.split(',')

    # Only ask for a fresh list of ready volumes when we need to
    # ie don't grab an update every iteration, no need to and it
    # introduces significant overhead
    def _ready():
            return [v for v in cc.volumes.list(search_opts={'status': 'available'}) 
                    if options.base_name in v.name
                    if options.template not in v.name]
    ready_vlist = _ready()
    instance_start_time = time.time()
    for i in xrange(options.instance_count):
        while len(ready_vlist) < 1:
            print('No ready volumes to boot, wait and rescan...')
            ready_vlist = _ready()
            counter = 0
            time.sleep(1)
            continue
        src_vol = random.choice(ready_vlist)
        create_kwargs = {}
        bdm = {'vda': src_vol.id + ':::0'}
        create_kwargs['block_device_mapping']  = bdm
        create_kwargs['nics'] = [{ 'net-id': options.net_UUID }]
        flavor_id = random.choice(flavor_list)
        try:
            nc.servers.create(src_vol.name, None, flavor_id,  **create_kwargs)
            ready_vlist.remove(src_vol)
        except Exception as ex:
            print 'Caught exception booting instance: %s' % ex
            pass
        counter += 1
        if counter % 10 == 0:
            time.sleep(5)
    print('Boot process completed in %s secs (elapsed test time  %s secs)' %
          (time.time() - instance_start_time, time.time() - start_time))
    # Now we just have to wait for the instances to become ACTIVE
    done_count = 0
    while done_count < options.instance_count:
        active_list = [s for s in nc.servers.list(search_opts={'status': 'ACTIVE'})
                       if options.base_name in s.name]
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

