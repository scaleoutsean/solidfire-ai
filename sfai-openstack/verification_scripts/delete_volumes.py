#!/usr/bin/python

from optparse import OptionParser
import os

from cinderclient import client as cinderclient
from novaclient.v1_1 import client as novaclient

USER = os.getenv('OS_USERNAME')
TENANT = os.getenv('OS_TENANT_NAME')
PASSWORD = os.getenv('OS_PASSWORD')
AUTH_URL = os.getenv('OS_AUTH_URL')

def process_options():
    config = {}
    usage = "usage: %prog [options]\ndelete_volumes.py."
    parser = OptionParser(usage, version='%prog 1.0')

    parser.add_option('-n', '--name', action='store',
                      type='string',
                      dest='name',
                      help='Base Name of instances to delete. Use \'all\' '
                           'to remove all volumes on the system.  '
                           '(Remember to include the delimeter \'-\') ')

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

    options = process_options()
    (cc, nc) = init_clients()

    vlist = cc.volumes.list()
    for v in vlist:
        if options.name == 'all' or options.name in v.display_name:
            if 'available' not in v.status.lower():
                cc.volumes.reset_state(v.id, 'available')
            try:
                cc.volumes.delete(v.id)
            except Exception as ex:
                print "Caught exception:%s" % ex
                pass
