# Windtunnel (beta)

Performance & stress testing for your FHIR server.

This is the first release to gauge the community interest and we'd love to hear your feedback on it. For feedback and known issues, [see here](https://github.com/FirelyTeam/Wind.Tunnel/issues).


## Setup

First, prepare the server under test with sample data. Either upload all [Synthea bundles](performance-data/) yourself or do:

1. Zip up all of the resource to upload with [atool](https://www.nongnu.org/atool/): `apack upload.zip performance-data/`
1. Upload zip with [Vonkloader](http://docs.simplifier.net/vonkloader/index.html): `vonkloader -file:upload.zip -collectionHandling:Split -server:http://<my server>`

### Install Python dependencies
1. Install Python dependencies using `pip` (if you don't have it, [install first](https://pip.pypa.io/en/stable/installing/)): `pip install influxdb jsonpath_rw statistics psutil pathlib fhirclient`

## Running performance tests

Run `start_performance_test.sh` - parameters supported are:

* `--backend` (required): backend in use by target host (`mongo`, `postgres`, `memory`, `sqlite`, or `sqlserver`)
* `--host` (optional): system under test (eg. `http://localhost`)
* `--influxdb` (required): InfluxDB intake to sends results to (eg. `http://grafana-locust-firely.westeurope.cloudapp.azure.com:9086`)
* `--duration` (optional): customise how long to run each test for. By default, each test is run for 5mins.

```sh
# example: run performance tests against localhost:4080
./start_performance_test.sh --backend mongo --host http://localhost:4080 --influxdb http://grafana-locust-firely.westeurope.cloudapp.azure.com:9086
```

## Viewing performance test results

Results are available on online:

1. Go to [inspect-particular-test-run](http://grafana-locust-firely.westeurope.cloudapp.azure.com:4000/d/DN0PLjKmk/inspect-particular-test-run)
1. In the `Select run` dropdown, select your particular test run
1. Copy the year+time timestamp and paste it into the `From:` field in the time range top-right
1. Paste the timestamp plus two hours into the `To:` field

See [gif](view-test-results.gif) of the process.

Aggregated results are available at [overview-of-all-runs-results](http://grafana-locust-firely.westeurope.cloudapp.azure.com:4000/d/lBAvi3Fiz/overview-of-all-runs-results).

## Running stress tests

Stress testing is different from performance testing: whereas performance testing will help you see how better (or worse) you're doing in different scenarios, stress testing will push your configuration to the max to see what you can handle.

Run `start_stress_test.sh` - parameters supported are:

* `--host` (required): system under test (eg. `http://localhost`)
* `--ignore-lock` (optional): allow stress test to run even while another performance or stress test is running

```sh
 ./start_stress_test.sh --host http://localhost
```

## Viewing stress test results

Open up the results on [http://localhost:8089](http://localhost:8089).

## Built With

* [Python](https://www.python.org/)
* [Locust](https://locust.io/) - An open source load testing tool
* [InfluxDB](https://github.com/influxdata/influxdb) - Scalable datastore for metrics, events, and real-time analytics
* [Grafana](https://github.com/grafana/grafana) - The tool for beautiful monitoring and metric analytics & dashboards for Graphite, InfluxDB & Prometheus & More


## Authors

* **Lilian Minne**
* **Vadim Peretokin**

## License

BSD 3-clause.
