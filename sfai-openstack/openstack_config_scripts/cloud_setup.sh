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

# set VOLUME_BACKEND_NAME to the name of your array
VOLUME_BACKEND_NAME="SolidFire"

# Setup 4 arrays corresponding to your Volume types and QoS settings
VOL_TYPES=( "mongo1-iops" "mongo2-iops" "mysql-iops" "LAMP-iops" )
MIN=(        5000          3000          10000        100       )
MAX=(        10000         8000          20000        1000      )
BURST=(      15000         10000         40000        2000      )

INDEX=0
for VOL_TYPE in "${VOL_TYPES[@]}"
do
   echo "Create Volume Type: ${VOL_TYPE}"
   TYPENAME_TYPEID=$(cinder type-create ${VOL_TYPE} | grep ${VOL_TYPE} | get_field 1)
   echo "Creating QoS Specs"
   QOS_ID=$(cinder qos-create ${VOL_TYPE} qos:minIOPS=${MIN[${INDEX}]} qos:maxIOPS=${MAX[${INDEX}]} qos:burstIOPS=${BURST[${INDEX}]} | grep id | get_field 2)
   echo "Setting volume backend name ..."
   cinder type-key ${TYPENAME_TYPEID} set volume_backend_name=${VOLUME_BACKEND_NAME}
   echo "Associating QoS specs with volume type .... "
   cinder qos-associate ${QOS_ID} ${TYPENAME_TYPEID}
   ((INDEX++))
done

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
