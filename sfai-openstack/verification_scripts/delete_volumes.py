#!/usr/bin/python

import os

from cinderclient import client as cinderclient
from novaclient.v1_1 import client as novaclient

USER = os.getenv('OS_USERNAME')
TENANT = os.getenv('OS_TENANT_NAME')
PASSWORD = os.getenv('OS_PASSWORD')
AUTH_URL = os.getenv('OS_AUTH_URL')

def init_clients():
    cc = cinderclient.Client('1', USER,
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
    for c in clist:
        if 'available' not in c.status.lower():
            cc.volumes.reset_state(c.id, 'available')
        try:
            cc.volumes.delete(c.id)
        except Exception as ex:
            print "Caught exception:%s" % ex
            pass
