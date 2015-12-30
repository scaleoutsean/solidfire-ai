#!/usr/bin/python

import os

from cinderclient import client as cinderclient
from novaclient.v2 import client as novaclient

USER = os.getenv('OS_USERNAME')
TENANT = os.getenv('OS_TENANT_NAME')
PASSWORD = os.getenv('OS_PASSWORD')
AUTH_URL = os.getenv('OS_AUTH_URL')

def init_clients():
    cc = cinderclient.Client('2', USER,
                              PASSWORD, TENANT,
                              AUTH_URL)
    nc = novaclient.Client(USER, PASSWORD,
                             TENANT, AUTH_URL,
                             service_type="compute")
    return cc, nc

if __name__ == '__main__':

    (cc, nc) = init_clients()

    clist = cc.volumes.list()
    print 'volume count is:%s' % len(clist)
    n_available = 0
    n_error = 0
    n_inuse = 0
    for c in clist:
        if 'error' in c.status:
            n_error += 1
        elif c.status == 'in-use':
            n_inuse += 1
        elif c.status == 'available':
            n_available += 1
        else:
            print "status: %s" % c.status
            break

    print "Avail: %s" % n_available
    print "Error: %s" % n_error
    print "In-Use: %s" % n_inuse
    print "Total: %s" % len(clist)
