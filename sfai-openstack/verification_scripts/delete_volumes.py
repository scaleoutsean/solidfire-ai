#!/usr/bin/python

import os
import time

from cinderclient import client as cinderclient
from novaclient.v1_1 import client as novaclient

USER = os.getenv('OS_USERNAME')
TENANT = os.getenv('OS_TENANT_NAME')
PASSWORD = os.getenv('OS_PASSWORD')
AUTH_URL = os.getenv('OS_AUTH_URL')

SKIP_VOLUME_ID = 'e5238420-120a-4fbf-ac18-416f33ee2c8a'

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
        if c.id == SKIP_VOLUME_ID:
            pass
        elif 'creating' in c.status:
            cc.volumes.reset_state(c.id, 'available')
            time.sleep(1)
            cc.volumes.delete(c.id)
            pass
        else:
            try:
                print 'skip'
            except Exception as ex:
                print "Caught exception:%s" % ex
                pass
