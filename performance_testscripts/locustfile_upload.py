from locust import HttpLocust, TaskSet, task
from locust.exception import StopLocust
from os import listdir
from os.path import isfile, join, realpath, dirname
from pathlib import Path
from reporter import Reporter
import json
import locust.events
import threading

exampleslocation = "synthea_output_1_00001-00100"

threadLock = threading.Lock()


class UploadResourcesSet(TaskSet):
    def setup(self):
        global files, exampleslocation
        files = [f for f in listdir(str(Path.cwd()) + "/" + exampleslocation) if isfile(join(str(Path.cwd()), exampleslocation, f))]
        files.sort(reverse=True)

    def process_bundle(self, filename):
        with open(filename) as json_data:
            bundle = json.load(json_data)
            bundle['type'] = "batch"

            for entry in bundle['entry']:
                self.add_request(entry)

            return bundle

    def add_request(self, entry):
        if 'id' in entry['resource']:
            entry['request'] = {
                "method": "PUT",
                "url": "%s/%s" % (entry['resource']['resourceType'],
                                  entry['resource']['id'])
            }
        else:
            entry['request'] = {
                "method": "POST",
                "url": entry['resource']['resourceType']
            }

    @task(1)
    def upload_resource(self):
        global files

        if len(files) <= 0:
            raise StopLocust()

        with threadLock:
            filename = files[-1]
            del files[-1]

        filepath = "%s/%s/%s" % (str(Path.cwd()), exampleslocation,
                                 filename)

        bundle = self.process_bundle(filepath)

        print("Uploading %s, %s bundles to go" % (filename, len(files)))
        self.client.post("/", name="(upload) Synthea bundle", headers={'Content-Type': 'application/json'}, json=bundle)


class VonkTaskSet(HttpLocust):
    task_set = UploadResourcesSet
    min_wait = 0
    max_wait = 1000

    def setup(self):
        self.reporter = Reporter(self.host, self.min_wait, self.max_wait, "upload")
        locust.events.request_success += self.reporter.request_success
        locust.events.request_failure += self.reporter.request_failure
        locust.events.hatch_complete += self.reporter.hatch_complete
        locust.events.quitting += self.reporter.stop
