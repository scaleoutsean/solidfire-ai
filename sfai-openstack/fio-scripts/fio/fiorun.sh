#!/bin/bash

cd "$(dirname "$0")"
RANDOM=$$$(date +%s)
profiles=(./profiles/*)
##selection=${profiles[$RANDOM % ${#profiles[*]}]}

while true
do
  
  selection=${profiles[$RANDOM % ${#profiles[@]} ]}
  filename="${selection##*/}"
  echo "filename is $filename"
  # Create filename.
  timestamp=$(date +%s)
  hostname=$(hostname -s)
  outputfile="$hostname-$timestamp-$filename.log"
  echo "Running fio profile $selection"
  fio --minimal $selection > $outputfile
  wput "$outputfile" ftp://ftp:password@172.27.1.41/logdump/
  sleep $[ ( $RANDOM % 360 )  + 1 ]s
done
