from locust import HttpLocust, TaskSet, task
from locust.clients import HttpSession
from locust.exception import ResponseError
from os import environ as env
from reporter import Reporter
import datetime
import locust.events
import logging
import sys
import time
import traceback


class VonkTaskSet(TaskSet):
    def setup(self):
        pass

    @task(1)
    def patient_with_observations(self):
        self.client.get("/Patient?identifier=80e5a344-2dec-4794-9ae2-6a4387be47a4&_revinclude=Observation:subject", name="(general) Patient + revinclude observations")

    @task(1)
    def patient_with_observations_and_reports(self):
        self.client.get("/Patient?identifier=80e5a344-2dec-4794-9ae2-6a4387be47a4&_revinclude=Observation:subject&_revinclude=DiagnosticReport:patient", name="(general) Patient + revinclude observations, diagnosticreport")

    @task(1)
    def one_patient(self):
        self.client.get("/Patient?name=Esmeralda517",
                        name="(general) Patient by name")

    @task(1)
    def name_and_birthday(self):
        self.client.get("/Patient?name=Abbott509&birthdate=ge1970",
                        name="(general) Patients by name and birthday")

    @task(1)
    def all_conditions(self):
        self.client.get("/Condition", name="(general) All Conditions")


class VonkLocust(HttpLocust):
    task_set = VonkTaskSet
    min_wait = 0
    max_wait = 1000

    sys.stderr = sys.stdout

    # # console_logger = logging.getLogger("console_logger")
    # console_logger = logging.getLogger("stderr")
    # print(console_logger)
    # # logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

    def setup(self):
        # don't record metric information for stress tests at the moment - Grafana not setup to display them
        if 'STRESS_TEST' not in env:
            self.reporter = Reporter(self.host, self.min_wait, self.max_wait, "general")
            locust.events.request_success += self.reporter.request_success
            locust.events.request_failure += self.reporter.request_failure
            locust.events.hatch_complete += self.reporter.hatch_complete
            locust.events.quitting += self.reporter.stop
