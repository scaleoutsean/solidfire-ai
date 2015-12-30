#!/usr/bin/python

""" This program will retype volumes 
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
    parser = OptionParser(usage, version='%prog 2.0')

    parser.add_option('-c', '--instance-count', action='store',
                      type='int',
                      default=2,
                      dest='instance_count',
                      help='Number of instances to boot (default = 2).')
    parser.add_option('-n', '--name', action='store',
                      type='string',
                      default='verification',
                      dest='volume_base_name',
                      help='Base name to use for new template volume ( -template will be added)')
    parser.add_option('--template', action='store',
                      type='string',
                      default='-template',
                      dest='template',
                      help='The suffix to designate the template (default: -template)')
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

if __name__ == '__main__':

    options = process_options()
    (cc, nc) = init_clients()
    start_time = time.time()

    created = [v for v in cc.volumes.list()
               if options.volume_base_name in v.name
               if options.template not in v.name]

    print 'Retyping volumes...'
    for vol in created:
        try:
            cc.volumes.retype(volume=vol.id,
                              volume_type=options.vol_type,
                              policy='never')
        except cinderclient.exceptions.BadRequest:
            pass
    print 'Total time was:%s seconds' % (time.time() - start_time)

