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

    parser.add_option('-n', '--name', action='store',
                      type='string',
                      dest='name')

    parser.add_option('-f', '--force', action='store',
                      type='string',
                      default=False,
                      dest='force')

    parser.add_option('-v', '--volume', action='store',
                      type='string',
                      dest='volume')

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
    cc.volume_snapshots.create(options.volume,
                       force=options.force, 
                       display_name=options.name)
