#!/usr/bin/env bash

# **create_images.sh**
# Simple script to build some glance images
# We're going to build some public images, that we
# want to test with
#  * Fedora 20
#  * Ubuntu 12.04
#  * Cirros 0.3.2


echo "Upload Fedora-20 image to glance..."
ret=`glance image-create --name Fedora-20  --is-public True --disk-format qcow2 --container-format bare --location http://download.fedoraproject.org/pub/fedora/linux/updates/20/Images/x86_64/Fedora-x86_64-20-20140407-sda.qcow2`
printf "%b\n" "$ret"

echo "Upload Ubuntu image to glance..."
ret=`glance image-create --name "Ubuntu 12.04" --is-public True --disk-format qcow2 --container-format bare --location http://uec-images.ubuntu.com/precise/current/precise-server-cloudimg-amd64-disk1.img`
printf "%b\n" "$ret"

echo "Upload cirros test image to glance..."
ret=`glance image-create --name cirros --is-public True --disk-format qcow2 --container-format bare --location http://download.cirros-cloud.net/0.3.2/cirros-0.3.2-x86_64-disk.img`
printf "%b\n" "$ret"

set +o xtrace

