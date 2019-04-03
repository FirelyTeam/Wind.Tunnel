from datetime import datetime
from influxdb import InfluxDBClient
from locust import events
from locust.clients import HttpSession
from locust.exception import ResponseError
from os import environ as env
import gevent
import locust.runners
import os
import socket
import traceback
import uuid
import sys
import psstats as ps
import test


class Reporter(object):

    def __init__(self, host, min_wait, max_wait, tests_type):
        self.host = host
        self.min_wait = min_wait
        self.max_wait = max_wait
        influxdbstring = env["INFLUXDB"]
        influxport = influxdbstring.split(":").pop()

        try:
            influxport = int(influxport)
        except ValueError:
            print("Invalid port number given ({}), defaulting to 8086").format(
                influxport)
            influxport = 8086

        influxhost = influxdbstring.split(":")
        influxhost.pop()
        influxhost = influxhost.pop().replace("//", "")

        self._client = InfluxDBClient(host=influxhost, port=influxport, database='data')
        self._user_count = locust.runners.locust_runner.num_clients
        # self._run_id = env["RUN_ID"]
        # self._team = env["TEAM"]
        self._hostname = socket.gethostname()
        self._finished = False
        self._points = []
        self._ps = ps.PSStats()

        self.sanity_test()
        self._client.create_database('data')

        self.tests_type = tests_type

        session = HttpSession(base_url="")
        statement = session.get(self.host + "/metadata").json()

        self.test_uuid = str(uuid.uuid4())
        self.test_start = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

        if 'software' in statement:
            self.server_version = statement['software']['version']
            self.server_name = statement['software']['name']
        else:
            self.server_version = 'unavailable'

        self.fhir_version = statement['fhirVersion']
        self.test_name = '{} {} v{} f{}'.format(
            env["TEST_DATE"], self.server_name, self.server_version, self.fhir_version)
        self.write_start_annotation(tests_type)


        self._background = gevent.spawn(self._run) # handle to your greenlet (think threads)

    def write_start_annotation(self, tests_type):
        title = "Start of {} tests with {} user{}".format(tests_type,
                                                          self._user_count,
                                                          '' if self._user_count <= 1 else 's')
        tags_field = '{}, {} user{}, v{}, {}, f{}, {}'.format(tests_type,
                                             self._user_count,
                                             '' if self._user_count <= 1 else 's',
                                             self.server_version,
                                             env["BACKEND"],
                                             self.fhir_version,
                                             env["TEST_DATE"])

        data = [{
            'measurement': 'start_annotation',
            'fields': {
                    'tags': tags_field,
                    'title': title,
                }
        }]
        self._client.write_points(data)

    def write_end_annotation(self, tests_type):
        title = "End of {} tests with {} user{}".format(tests_type,
                                                          self._user_count,
                                                          '' if self._user_count <= 1 else 's')
        tags_field = '{}, {} user{}, v{}, {}, f{}, {}'.format(tests_type,
                                             self._user_count,
                                             '' if self._user_count <= 1 else 's',
                                             self.server_version,
                                             env["BACKEND"],
                                             self.fhir_version,
                                             env["TEST_DATE"])

        data = [{
            'measurement': 'end_annotation',
            'fields': {
                    'tags': tags_field,
                    'title': title,
                }
        }]
        self._client.write_points(data)

    def _run(self): # greenlet function
        while True:
            if self._points:
                self._send_ps_stats()
                # Buffer points, so that a locust greenlet will write to the new list
                # instead of the one that has been sent into influx client
                points_copy = list(self._points)
                del self._points[:]
                self._client.write_points(points_copy)
            else:
                if self._finished:
                    break
            gevent.sleep(0.5)

    def _send_vu_count(self):
        point = self._point_template("user_count")
        point["fields"].update({"value": self._user_count})
        self._points.append(point)

    def _send_ps_stats(self):
        cpu = self._point_template("loadgen_cpu")
        ctuple = self._ps.get_cpu_times_percent()
        for k, v in ctuple._asdict().items():
            cpu["fields"].update({k: v})
        self._points.append(cpu)

        mem = self._point_template("loadgen_memory")
        mtuple = self._ps.get_memory_usage()
        for k, v in mtuple._asdict().items():
            mem["fields"].update({k: v})
        self._points.append(mem)

        vmem = self._point_template("loadgen_virtual_memory")
        vmtuple = self._ps.get_virtual_mempry()
        for k, v in vmtuple._asdict().items():
            vmem["fields"].update({k: v})
        self._points.append(vmem)

        mem_percentage = self._point_template("loadgen_memory_percentage")
        mem_percentage["fields"].update({"value": self._ps.get_memory_percentage()})
        self._points.append(mem_percentage)

        iodict = self._ps.get_net_io_counters()
        for k,v in iodict.items():
            io = self._point_template("loadgen_io")
            io["tags"].update({"interface": k})
            for field, value in v.items():
                io["fields"].update({field:value})
            self._points.append(io)

    def _point_template(self, measurement):
        p = {
            "measurement": measurement,
            "tags": {
                "loadgen": self._hostname,
                "pid": self._ps.get_pid(),
                "test_run": self.test_uuid,
                "test_start": self.test_start,
                "test_run_start": env["TEST_DATE"],
                "vonk_version": self.server_version,
                "fhir_version": self.fhir_version,
                "user_count": self._user_count,
                "test_name": self.test_name,
                "min_wait": self.min_wait,
                "max_wait": self.max_wait
            },
            "time": datetime.utcnow().isoformat(),
            "fields": {}
        }
        return p

    def stop(self):
        self._send_vu_count()
        self.write_end_annotation(self.tests_type)
        self._user_count=0
        self._send_vu_count()
        self._finished = True
        self._background.join()

    def hatch_complete(self, user_count):
        self._send_vu_count()

    def request_success(self, request_type, name,
                        response_time, response_length):
        if name == "test_setup":
            return

        point = self._point_template("response_time")
        point["tags"].update({
            "query_name": name,
            "name": name,
            "loadgen": self._hostname})
        point["fields"].update({"response_time": response_time})
        self._points.append(point)
        self._send_vu_count()

    def request_failure(self, request_type, name,
                        response_time, exception):
        if name == "test_setup":
            return

        point = self._point_template("request_failure_duration")
        point["tags"].update({
            "request_type": request_type,
            "name": name,
            "loadgen": self._hostname})
        point["fields"].update({
            "response_time": response_time,
            "exception": "{}".format(exception)})
        self._points.append(point)
        self._send_vu_count()

    def sanity_test(self):
        self.environment_sanity_test()
        self.endpoint_sanity_test()
        self.influx_sanity_test()

    def environment_sanity_test(self):
        if 'TEST_DATE' not in env:
            sys.exit("$TEST_DATE environment variable is missing - are you running start*.sh?")

        if 'BACKEND' not in env:
            sys.exit("$BACKEND environment variable is missing - are you running start*.sh?")

    def endpoint_sanity_test(self):
        session = HttpSession(base_url="")

        with session.get(self.host + "/Patient?given=Mariano451&family=Bashirian129",
                         catch_response=True, name="Sanity test") as response:
            try:
                test.checkResponse(response.status_code, 200)
                bundle = response.json()
                test.checkTotalAboveZero(self, bundle, True)
            except ResponseError:
                sys.exit('Sanity test failed, /Patient?given=Mariano451&family=Bashirian129 returned nothing. Have you uploaded the test dataset?')

    def influx_sanity_test(self):
        try:
            self._client.get_list_database()
        except Exception as e:
            print(traceback.format_exc())
            sys.exit('InfluxDB sanity test failed, could not retrieve database list')
