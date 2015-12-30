#!/usr/bin/python

from optparse import OptionParser
import os

from cinderclient import client as cinderclient
from novaclient.v2 import client as novaclient

USER = os.getenv('OS_USERNAME')
TENANT = os.getenv('OS_TENANT_NAME')
PASSWORD = os.getenv('OS_PASSWORD')
AUTH_URL = os.getenv('OS_AUTH_URL')

def process_options():
    config = {}
    usage = "usage: %prog [options]\ndelete_instances.py."
    parser = OptionParser(usage, version='%prog 1.0')

    parser.add_option('-n', '--name', action='store',
                      type='string',
                      dest='name',
                      default='verification',
                      help='Base Name of instances to delete')

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

    ilist = nc.servers.list()
    print 'instance count is:%s' % len(ilist)
    for i in ilist:
        if options.name == 'all' or options.name in i.name:
            if 'error' in i.status.lower():
                try:
                    nc.servers.reset_state(i.id, 'active')
                except:
                    print "Could not reset state of errored VM."
                    pass
            try:
                nc.servers.delete(i.id)
            except Exception as ex:
                print "Caught exception:%s" % ex
                pass
