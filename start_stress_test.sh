#!/usr/bin/env bash

export TEST_DATE=$(date "+%Y-%m-%d %H:%M:%S CET")
export STRESS_TEST="true"

# Script setup
bold=$(tput bold)
normal=$(tput sgr0)

# Capture command-line arguments
while [[ "$#" > 0 ]]; do case $1 in
  -h|--host) host="$2"; shift;;
  -b|--backend) backend="$2"; shift;;
  -i|--ignore-lock) ignorelock="$2"; shift;;
  # -b|--backend) backend=1;;
  *) echo "Unknown parameter passed: $1"; exit 1;;
esac; shift; done

if ! [[ "$host" =~ ^https?://.+ ]]; then
    echo "--host needs to start with http:// or https://"
    exit
fi

# Ensure only one instance of the performance test is running
# Credit: https://linuxaria.com/howto/linux-shell-introduction-to-flock
lock="/tmp/vonk-testing"
if [[ ! -v ignorelock ]]; then
  exec 200>$lock
  flock -n 200
  if [ $? -ne 0 ]; then
    echo "Another test is ${bold}already${normal} running - quitting."
    exit 1
  fi

  pid=$$
  echo $pid 1>&200
fi



# Sanity check that we can connect to Vonk
test_command="curl -sL \
    -w "%{http_code}\\n" \
    "$host/Patient?_format=json" \
    -o /dev/null \
    --connect-timeout 10 \
    --max-time 5"
if [ $($test_command) != "200" ] ;
then
  echo "Couldn't connect to ${bold}$host${normal} - is server the up, port correct, firewall open, etc.?"
  exit
fi

# echo "${bold}Restoring${normal} MongoDB data"
# ssh loaderdb@137.117.205.196 'mongorestore --dir "C:\Users\loaderdb\Desktop\dump"'

locust --locustfile=performance_testscripts/locustfile.py --host=$host
