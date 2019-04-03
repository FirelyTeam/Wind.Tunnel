from locust import HttpLocust, TaskSet, task
from locust.exception import StopLocust
import json
from jsonpath_rw import jsonpath, parse
import threading
import math
from reporter import Reporter
import locust.events

# locust --host=http://localhost:4080 --locustfile=locustfile_pagination.py --no-web --clients=100 --hatch-rate=100  --run-time=5min

threadLock = threading.Lock()


class PageThroughResultsSet(TaskSet):
    def setup(self):
        global ids, limit
        ids = []

        bundle = self.client.get("/Patient?_count=50", name="test_setup").json()
        total = [match.value for match in parse("$.total").find(bundle)]
        limit = total[0] / 5

        while(len(ids) <= limit):
            ids.extend([match.value for match in parse("$['entry'][*]['fullUrl']").find(bundle)])

            if len([link for link in bundle['link'] if link['relation'] == 'next']) <= 0:
                break

            next_link = ([link for link in bundle['link'] if link['relation'] == 'next'])[0]['url']
            bundle = self.client.get(next_link, name="test_setup").json()

    @task(1)
    def process_pages(self):
        global ids, limit

        with threadLock:
            if limit < 0:
                raise StopLocust()
            else:
                response = self.client.delete(ids[limit-1], name="(delete) Patient delete")
                if response.status_code != 204:
                    print("Unexpected response code on patient delete: {}"
                          .format(response.status_code))
                limit = limit - 1


class VonkTaskSet(HttpLocust):
    task_set = PageThroughResultsSet
    min_wait = 0
    max_wait = 1000

    def setup(self):
        self.reporter = Reporter(self.host, self.min_wait, self.max_wait, "delete")
        locust.events.request_success += self.reporter.request_success
        locust.events.request_failure += self.reporter.request_failure
        locust.events.hatch_complete += self.reporter.hatch_complete
        locust.events.quitting += self.reporter.stop
