#!/usr/bin/env bash

# **verify_install.sh**
# This script is made up of the devstack exercises tests
# It's a simple sanity check to make sure that a new
# deployment is working properly.
# Run through and hit some of the basic API calls
# utilizing the client.

# Assumptions:
#    Download and Source your creds file before running
#    Running on the controller (has the needed python client pkgs installed)

# Verification steps:
# 1. Create/Delete a verification tenant and user
# 2. Create a test image in Glance (Cirros test image)
# 3. Boot an instance using the Cirros image
# 4. Create a new Cinder Volume
# 5. Attach newly created volume to our test instance
# 6. Detach the volume
# 7. Delete the volume
# 8. Delete the instance

ACTIVE_TIMEOUT=120 
DELETE_TIMEOUT=120
VOL_NAME=test-volume 

function create_get_tenant
{
  local tenant_name=$1
  local tenant_id=`keystone tenant-list | awk '/\|[[:space:]]*'"$tenant_name"'[[:space:]]*\|.*\|/ {print $2}'`
  if [ -n "$tenant_id" ]; then
    echo $tenant_id
  else
    keystone tenant-create --name "$tenant_name" | awk '/\|[[:space:]]*id[[:space:]]*\|.*\|/ {print $4}'
  fi
}

function delete_tenant
{
  local tenant_id=$1
  keystone tenant-delete "$tenant_id"
}

function get_user_id 
{
    local user_name=$1
    keystone user-list | awk '/^\|[^|]*\|[[:space:]]*'"$user_name"'[[:space:]]*\|.*\|/ {print $2}'
}

function user_delete
{
  local user_id=$1
  keystone user-delete "$user_id"
}

function die_if_not_set {
    local exitcode=$?
    FXTRACE=$(set +o | grep xtrace)
    set +o xtrace
    local line=$1; shift
    local evar=$1; shift
    if ! is_set $evar || [ $exitcode != 0 ]; then
        die $line "$*"
    fi
    $FXTRACE
}

function die {
    local exitcode=$?
    set +o xtrace
    local line=$1; shift
    if [ $exitcode == 0 ]; then
        exitcode=1
    fi
    backtrace 2
    err $line "$*"
    # Give buffers a second to flush
    sleep 1
    exit $exitcode
}

function is_set {
    local var=\$"$1"
    eval "[ -n \"$var\" ]" # For ex.: sh -c "[ -n \"$var\" ]" would be better, but several exercises depends on this
}

function get_field {
    while read data; do
        if [ "$1" -lt 0 ]; then
            field="(\$(NF$1))"
        else
            field="\$$(($1 + 1))"
        fi
        echo "$data" | awk -F'[ \t]*\\|[ \t]*' "{print $field}"
    done
}

function err {
    local exitcode=$?
    errXTRACE=$(set +o | grep xtrace)
    set +o xtrace
    local msg="[ERROR] ${BASH_SOURCE[2]}:$1 $2"
    echo $msg 1>&2;
    if [[ -n ${SCREEN_LOGDIR} ]]; then
        echo $msg >> "${SCREEN_LOGDIR}/error.log"
    fi
    $errXTRACE
    return $exitcode
}

function backtrace {
    local level=$1
    local deep=$((${#BASH_SOURCE[@]} - 1))
    echo "[Call Trace]"
    while [ $level -le $deep ]; do
        echo "${BASH_SOURCE[$deep]}:${BASH_LINENO[$deep-1]}:${FUNCNAME[$deep-1]}"
        deep=$((deep - 1))
    done
}
echo "Create and delete verification project and user..."
tenant_id=`create_get_tenant "verification"`
user_id=`keystone user-create --name verification --tenant-id "$tenant_id" --pass password --email test@verify.com | awk '/\|[[:space:]]*id[[:space:]]*\|.*\|/ {print $4}'`
echo `keystone user-delete "$user_id"`
echo `keystone tenant-delete "$tenant_id"`

echo "Upload cirros test image to glance..."
ret=`glance image-create --name cirros --is-public True --disk-format qcow2 --container-format bare --location http://download.cirros-cloud.net/0.3.2/cirros-0.3.2-x86_64-disk.img`
printf "%b\n" "$ret"

echo "Boot a test instance..."
IMAGE=$(glance image-list | egrep "cirros" | get_field 1)
die_if_not_set $LINENO IMAGE "Failure getting image $DEFAULT_IMAGE_NAME"

INSTANCE_TYPE=$(nova flavor-list | head -n 4 | tail -n 1 | get_field 1)
die_if_not_set $LINENO INSTANCE_TYPE "Failure retrieving INSTANCE_TYPE"

VM_UUID=$(nova boot --flavor $INSTANCE_TYPE --image $IMAGE test | grep ' id ' | get_field 2)
die_if_not_set $LINENO VM_UUID "Failure launching $VM_NAME"

# Check that the status is active within ACTIVE_TIMEOUT seconds
if ! timeout $ACTIVE_TIMEOUT sh -c "while ! nova show $VM_UUID | grep status | grep -q ACTIVE; do sleep 1; done"; then
    die $LINENO "server didn't become active!"
fi

# Create a new volume
start_time=$(date +%s)
cinder create --display-name $VOL_NAME --display-description "test volume: $VOL_NAME" 10 || \
    die $LINENO "Failure creating volume $VOL_NAME"
if ! timeout $ACTIVE_TIMEOUT sh -c "while ! cinder list | grep $VOL_NAME | grep available; do sleep 1; done"; then
    die $LINENO "Volume $VOL_NAME not created"
fi
end_time=$(date +%s)
echo "Completed cinder create in $((end_time - start_time)) seconds"

# Get volume ID
VOL_ID=$(cinder list | grep $VOL_NAME | head -1 | get_field 1)
die_if_not_set $LINENO VOL_ID "Failure retrieving volume ID for $VOL_NAME"

# Attach to server
DEVICE=/dev/vdb
start_time=$(date +%s)
nova volume-attach $VM_UUID $VOL_ID $DEVICE || \
    die $LINENO "Failure attaching volume $VOL_NAME to $VM_NAME"
if ! timeout $ACTIVE_TIMEOUT sh -c "while ! cinder list | grep $VOL_NAME | grep in-use; do sleep 1; done"; then
    die $LINENO "Volume $VOL_NAME not attached to $VM_NAME"
fi
end_time=$(date +%s)
echo "Completed volume-attach in $((end_time - start_time)) seconds"

VOL_ATTACH=$(cinder list | grep $VOL_NAME | head -1 | get_field -1)
die_if_not_set $LINENO VOL_ATTACH "Failure retrieving $VOL_NAME status"
if [[ "$VOL_ATTACH" != $VM_UUID ]]; then
    die $LINENO "Volume not attached to correct instance"
fi

# Clean up
# --------

# Detach volume
start_time=$(date +%s)
nova volume-detach $VM_UUID $VOL_ID || die $LINENO "Failure detaching volume $VOL_NAME from $VM_NAME"
if ! timeout $ACTIVE_TIMEOUT sh -c "while ! cinder list | grep $VOL_NAME | grep available; do sleep 1; done"; then
    die $LINENO "Volume $VOL_NAME not detached from $VM_NAME"
fi
end_time=$(date +%s)
echo "Completed volume-detach in $((end_time - start_time)) seconds"

# Delete volume
start_time=$(date +%s)
cinder delete $VOL_ID || die $LINENO "Failure deleting volume $VOL_NAME"
if ! timeout $ACTIVE_TIMEOUT sh -c "while cinder list | grep $VOL_NAME; do sleep 1; done"; then
    die $LINENO "Volume $VOL_NAME not deleted"
fi
end_time=$(date +%s)
echo "Completed cinder delete in $((end_time - start_time)) seconds"

# Delete instance
nova delete $VM_UUID || die $LINENO "Failure deleting instance $VM_NAME"
if ! timeout $DELETE_TIMEOUT sh -c "while nova list | grep -q $VM_UUID; do sleep 1; done"; then
    die $LINENO "Server $VM_NAME not deleted"
fi

glance image-delete $IMAGE || die $LINENO "Failure deleting image $VM_NAME"

set +o xtrace

