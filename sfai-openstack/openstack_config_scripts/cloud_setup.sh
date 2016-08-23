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
TRUSTY_URL=https://cloud-images.ubuntu.com/trusty/current/trusty-server-cloudimg-amd64-disk1.img
PRECISE_URL=https://cloud-images.ubuntu.com/precise/current/precise-server-cloudimg-amd64-disk1.img
FEDORA_URL=https://download.fedoraproject.org/pub/fedora/linux/releases/23/Cloud/x86_64/Images/Fedora-Cloud-Base-23-20151030.x86_64.qcow2
CENTOS6_URL=http://cloud.centos.org/centos/6/images/CentOS-6-x86_64-GenericCloud.qcow2
CENTOS7_URL=http://cloud.centos.org/centos/7/images/CentOS-7-x86_64-GenericCloud.qcow2
WINDOWS_IMG_FILE=

echo "Creating Glance images..."
glance image-create --name 'Ubuntu Precise' --disk-format qcow2 --container-format bare --is-public true --copy-from $PRECISE_URL --progress
glance image-create --name 'Ubuntu Trusty' --disk-format qcow2 --container-format bare --is-public true --copy-from $TRUSTY_URL --progress
glance image-create --name 'Fedora 23' --disk-format qcow2 --container-format bare --is-public true --copy-from $FEDORA_URL --progress
glance image-create --name 'CentOS 6' --disk-format qcow2 --container-format bare --is-public true --copy-from $CENTOS6_URL --progress
glance image-create --name 'CentOS 7' --disk-format qcow2 --container-format bare --is-public true --copy-from $CENTOS7_URL --progress
#glance image-create --name 'Windows2012R2-Eval' --disk-format qcow2 --container-format bare --is-public true --file $WINDOWS_IMG_FILE --progress

# --- setup Volume Types ---
# set VOLUME_BACKEND_NAME to the name of your array
VOLUME_BACKEND_NAME="solidfire"

cinder type-create solidfire
cinder type-key solidfire set volume_backend_name=$VOLUME_BACKEND_NAME

# Setup 4 arrays corresponding to your Volume types and QoS settings
VOL_TYPES=( "silver" "bronze" "gold" "webserver" "platinum" )
DESCRIPTION=( '$[$1.12/GB/month]' '$[0.50/GB/month]' '[$2.10/GB/month]' '[$0.35/GB/month]' '[$3.00/GB/month]' )
MIN=(        500    100      1000   100       2000    )
MAX=(        800    200      1500  1000       2400    )
BURST=(      900    250      1700  1500       2500    )

INDEX=0
for VOL_TYPE in "${VOL_TYPES[@]}"
do
   echo "Create Volume Type: ${VOL_TYPE}"
   TYPE_DESC="IOPS=${MIN[${INDEX}]}/${MAX[${INDEX}]}/${BURST[${INDEX}]} ${DESCRIPTION[${INDEX}]}"
   TYPENAME_TYPEID=$(cinder type-create --description "${TYPE_DESC}" ${VOL_TYPE} | grep ${VOL_TYPE} | get_field 1)
   echo "Creating QoS Specs"
   QOS_ID=$(cinder qos-create ${VOL_TYPE}-qos qos:minIOPS=${MIN[${INDEX}]} qos:maxIOPS=${MAX[${INDEX}]} qos:burstIOPS=${BURST[${INDEX}]} | grep id | get_field 2)
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

echo "Create a Demo Project and user..."
openstack project create demo
read -s -p "Enter password for 'demo' user: " PASSWD
openstack user create --project demo --password $PASSWD demo

#openstack keypair create --public-key .ssh/id_rsa.pub default-key

