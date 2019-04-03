#!/usr/bin/env bash

host=http://localhost:4080
duration=5m

export TEST_DATE=$(TZ=CET date "+%Y-%m-%d %H:%M:%S CET")
export TERM=xterm

# Script setup
bold=$(tput bold)
normal=$(tput sgr0)


# Capture command-line arguments
while [[ "$#" > 0 ]]; do case $1 in
  -h|--host) host="$2"; shift;;
  -b|--backend) backend="$2"; shift;;
  -d|--duration) duration="$2"; shift;;
  -i|--influxdb) influxdb="$2"; shift;;
  *) echo "Unknown parameter passed: $1"; exit 1;;
esac; shift; done

# Argument sanity checks
if [ "$backend" != "mongo" ] && [ "$backend" != "postgres" ] && [ "$backend" != "memory" ] && [ "$backend" != "sqlite" ] && [ "$backend" != "sqlserver" ]; then
	echo "${bold}--backend${normal} needs to be one of: mongo, memory, sqlite, postgres, or sqlserver"
	exit
fi
export BACKEND=$backend

if ! [[ "$host" =~ ^https?://.+ ]]; then
  echo "${bold}--host${normal} needs to start with http:// or https://"
  exit
fi

if [ -z ${influxdb+x} ]; then
  echo "${bold}--influxdb${normal} not mentioned; which database should we send results to?"
  exit
fi
export INFLUXDB=$influxdb

# Ensure only one instance of the performance test is running (locally...)
# Credit: https://linuxaria.com/howto/linux-shell-introduction-to-flock
lock="/tmp/performance-testing"

exec 200>$lock
flock -n 200
if [ $? -ne 0 ]; then
  echo "Another test is ${bold}already${normal} running - quitting."
  exit 1
fi

pid=$$
echo $pid 1>&200

# Sanity check that we can connect to the server under test
test_command="curl -sL \
    -w "%{http_code}\\n" \
    "$host/Patient?_format=json\&_count=1" \
    -o /dev/null \
    --connect-timeout 20 \
    --max-time 20"
if [ $($test_command) != "200" ] ;
then
  echo "Couldn't connect to ${bold}$host${normal} - is server the up, port correct, firewall open, etc.?"
  exit
fi

# Get FHIR and server version
metadata_statement=$(curl -sk "$host/metadata?_format=json")
fhirVersion=$(jq -M -r '"\(.fhirVersion)"' <<< "$metadata_statement")
serverVersion=$(jq -M -r '"\(.software.version)"' <<< "$metadata_statement")

TEST_NAME="$TEST_DATE v$serverVersion f$fhirVersion"

function report_patient_count {
  patients_bundle=$(curl -sk "$host/Patient?_format=json")
  patient_count=$(jq -M -r '"\(.total)"' <<< "$patients_bundle")

  echo "$patient_count patients on the host server."
}

echo "Test $TEST_NAME start:"
report_patient_count

# Run actual tests with 1, 20, and 40 users
for i in 1 20 40
do
   echo "Running ${bold}general${normal} GET queries with ${bold}$i${normal} user(s) against $host"
   start_time=$(date +%s%N)
   locust --locustfile=performance_testscripts/locustfile.py --host="$host" --no-web --hatch-rate=$i --clients=$i \
     --only-summary --run-time=$duration 2>&1
   sleep 10s

   echo "Running ${bold}pagination${normal} queries with ${bold}$i${normal} user(s) against $host"
   start_time=$(date +%s%N)
   locust --locustfile=performance_testscripts/locustfile_pagination.py --host=$host --no-web --hatch-rate=$i --clients=$i \
     --only-summary --run-time=$duration 2>&1
   sleep 10s
done

echo "${bold}Deleting${normal} fifth of the Patients using 40 users"
locust --locustfile=performance_testscripts/locustfile_delete.py --host=$host --no-web --hatch-rate=40 --clients=40 --only-summary 2>&1
sleep 10s

# Re-add the sanity test patient back in
curl --silent -X POST -d @performance_testscripts/Abbott509_Esmeralda517_51.json -H "Content-Type: application/json" $host > /dev/null

echo "After deleting patients:"
report_patient_count

# Re-run tests with 40 users only
for i in 40
do
   echo "Running ${bold}general${normal} GET queries with ${bold}$i${normal} user(s) against $host"
   start_time=$(date +%s%N)
   locust --locustfile=performance_testscripts/locustfile.py --host=$host --no-web --hatch-rate=$i --clients=$i \
     --only-summary --run-time=$duration 2>&1
   sleep 10s

   echo "Running ${bold}pagination${normal} queries with ${bold}$i${normal} user(s) against $host"
   start_time=$(date +%s%N)
   locust --locustfile=performance_testscripts/locustfile_pagination.py --host=$host --no-web --hatch-rate=$i \
     --clients=$i --only-summary --run-time=$duration 2>&1
   sleep 10s
done

# Upload Synthea data with 1 and 20 users
for i in 1 20
do
   echo "Running ${bold}upload${normal} queries with ${bold}$i${normal} user(s) against $host"
   start_time=$(date +%s%N)
   locust --locustfile=performance_testscripts/locustfile_upload.py --host="$host" --no-web --hatch-rate=$i --clients=$i \
     --run-time=$duration 2>&1
   sleep 10s
done


RUN_END=$(date "+%Y-%m-%d %H:%M:%S CET")

echo "Final count:"
report_patient_count

echo "Performance run ${bold}finished${normal}."
