import psutil
import time
import numpy
import monotonic


class PSStats:

    def __init__(self):
        self.p = psutil.Process()
        self.net_io_cache = {"timestamp": monotonic.monotonic(), "net_io": psutil.net_io_counters(pernic=True)}

    def get_cpu_times_percent(self):
        return psutil.cpu_times_percent()

    def get_memory_usage(self):
        return self.p.memory_full_info()

    def get_memory_percentage(self):
        return psutil.virtual_memory().percent

    def get_virtual_mempry(self):
        return psutil.virtual_memory()

    def get_net_io_counters(self):
        result = {}
        current_timestamp = monotonic.monotonic()
        interval_length = current_timestamp - self.net_io_cache["timestamp"]
        net_io_current = psutil.net_io_counters(pernic=True)
        for key, tup in net_io_current.items():
            result_if = {key: self._diff_tuples(interval_length, tup, self.net_io_cache["net_io"][key])}
            result.update(result_if)
        self.net_io_cache["timestamp"] = current_timestamp
        self.net_io_cache["net_io"] = net_io_current
        return result

    def _diff_tuples(self, interval, latest, old):
        diff_array = (numpy.array(latest) - numpy.array(old))
        diff = {}
        for index, value in enumerate(diff_array):
            diff.update({old._fields[index] : int(value / interval)})
        return diff

    def get_pid(self):
        return self.p.pid


