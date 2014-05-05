 PASTE MODE  ~/solidfire-ai/scripts/setup_ai_environment.sh   CWD: /Users/jgriffith/solidfire-ai   Line: 1/45:1
#!/usr/bin/env bash

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

# Modify these to your local http server if you have one or to point to any custome images you've created
PRECISE_URL=http://uec-images.ubuntu.com/releases/12.04/release/ubuntu-12.04-server-cloudimg-amd64-disk1.img
FEDORA_URL=http://download.fedoraproject.org/pub/fedora/linux/releases/20/Images/x86_64/Fedora-x86_64-20-20131211.1-sda.qcow2
CENTOS_URL=http://repos.fedorapeople.org/repos/openstack/guest-images/centos-6.5-20140117.0.x86_64.qcow2

echo "Fetching image files..."
# We prefer downloading the image first, then passing it to glance
wget $PRECISE_URL
wget $FEDORA_URL
wget $CENTOS_URL

echo "Creating Glance images..."
glance image-create --name 'Ubuntu Precise' --disk-format qcow2 --container-format bare --is-public true < ubuntu-12.04-server-cloudimg-amd64-disk1.img
glance image-create --name 'Fedora 20' --disk-format qcow2 --container-format bare --is-public true < Fedora-x86_64-20-20131211.1-sda.qcow2
glance image-create --name 'CentOS 6.5' --disk-format qcow2 --container-format bare --is-public true < centos-6.5-20140117.0.x86_64.qcow2

echo "Create Volume Types that map to QoS settings..."
LOW_TYPEID=$(cinder type-create low-iops | grep low-iops | get_field 1)
MED_TYPEID=$(cinder type-create med-iops | grep med-iops | get_field 1)
HIGH_TYPEID=$(cinder type-create high-iops | grep high-iops | get_field 1)

echo "Assigning Extra-Specs to newly created Types..."
cinder type-key $LOW_TYPEID set qos:minIOPS=800 qos:maxIOPS=1000 qos:burstIOPS=1000
cinder type-key $MED_TYPEID set qos:minIOPS=1200 qos:maxIOPS=1600 qos:burstIOPS=1600
cinder type-key $HIGH_TYPEID set qos:minIOPS=1600 qos:maxIOPS=2000 qos:burstIOPS=2000

echo "Created Types and Extra-Specs:"
cinder extra-specs-list


echo "Enable ping/ssh security rules..."
nova secgroup-add-rule default icmp -1 -1 0.0.0.0/0
nova secgroup-add-rule default tcp 22 22 0.0.0.0/0

echo "Generate a new RSA key..."
nova keypair-add default_key > default_key.pem
chmod 600 default_key.pem
echo "Create a Memeber role in keystone..."
keystone role-create --name=Member
