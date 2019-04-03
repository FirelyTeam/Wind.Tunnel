from locust import HttpLocust, TaskSet, task
from locust.exception import StopLocust
from reporter import Reporter
import json
import locust.events

# locust --host=http://localhost:4080 --locustfile=locustfile_pagination.py --no-web --clients=100 --hatch-rate=100  --run-time=5min


class PageThroughResultsSet(TaskSet):
    def on_start(self):
        self.next_link = ""

        response = self.client.get("/CarePlan?_count=10", name="test_setup").json()
        self.next_link = ([link for link in response['link'] if link['relation'] == 'next'])[0]['url']

    @task(1)
    def process_pages(self):
        response = self.client.get(self.next_link, name="(pagination) Iterate thru /Careplan response (10 items per)").json()
        next_links = ([link for link in response['link'] if link['relation'] == 'next'])

        if len(next_links) >= 1:
            self.next_link = next_links[0]['url']
        else:
            raise StopLocust()


class VonkTaskSet(HttpLocust):
    task_set = PageThroughResultsSet
    min_wait = 0
    max_wait = 1000

    def setup(self):
        self.reporter = Reporter(self.host, self.min_wait, self.max_wait, "pagination")
        locust.events.request_success += self.reporter.request_success
        locust.events.request_failure += self.reporter.request_failure
        locust.events.hatch_complete += self.reporter.hatch_complete
        locust.events.quitting += self.reporter.stop
