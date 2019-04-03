#!/usr/bin/env python2

# postprocess_server_telemetry.py --end-time='1534492963504859302' --from-time='1534492960942397161' --test-name="2018-08-17 10:02:40 CET v0.7.1.1-beta f3.0.1"  --user-count=1 --server-version="0.7.1.1-beta"

from argparse import ArgumentParser
from influxdb import InfluxDBClient
import statistics

parser = ArgumentParser()
parser.add_argument("-t", "--test-name", dest="testname", metavar="name",
                    help="Test name to parse", required=True)
parser.add_argument("-u", "--user-count", dest="usercount", metavar="count",
                    help="Number of user used for the particular test run", required=True)
parser.add_argument("-s", "--server-version", dest="serverversion", metavar="version",
                    help="Server version used in the test", required=True)
parser.add_argument("-f", "--from-time", dest="fromtime", metavar="timestamp",
                    help="Unix nanosecond timestamp for the start of the test run", required=True)
parser.add_argument("-e", "--end-time", dest="endtime", metavar="timestamp",
                    help="Unix nanosecond timestamp for the start of the test run", required=True)
parser.add_argument("-q", "--quiet",
                    action="store_false", dest="verbose", default=True,
                    help="don't print status messages to stdout")

args = parser.parse_args()

client = InfluxDBClient(host='grafana-locust-firely.westeurope.cloudapp.azure.com', port=8086, database='telegraf_remote')


def process_results(series, measurement_name, output_measurement_name="", output_datatype="", invert_percent=False):
    if args.verbose:
        print("Data to process:        {}".format(locals()))

    if output_measurement_name == "":
        output_measurement_name = measurement_name

    results = client.query("""
    select * from {} where time >= {}ns and time <= {}ns
    """.format(series, args.fromtime, args.endtime))

    measurements = [measurement[measurement_name] for measurement in results.get_points()]
    if args.verbose:
        print("Measurements extracted: {}".format(measurements))

    if not measurements:
        return

    measurements_median = statistics.median(measurements)

    if output_datatype == "int":
        measurements_median = int(measurements_median)
    elif output_datatype == "float":
        measurements_median = float(measurements_median)

    if invert_percent:
        measurements_median = (100-measurements_median)

    data = [{
        'measurement': 'median',
        "tags": {
            "measurement_name": output_measurement_name,
            "user_count": args.usercount,
            "server_version": args.serverversion,
            "test_name": args.testname
        },
        "fields": {}
    }]
    data[0]['fields'][series] = measurements_median
    if args.verbose:
        print("value is {} for {} from {}".format(measurements_median, output_measurement_name, series))

    client.write_points(data)


process_results("win_cpu", "Percent_Idle_Time", output_measurement_name="Percent_CPU_Time", output_datatype="float", invert_percent=True)
process_results("win_mem", "Available_Bytes", output_datatype="int")
