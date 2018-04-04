# The workaround I am currently using involves:
# 1) Inheriting a new class from simpy.Store
# 2) Patching _do_put and _do_get to include custom call backs
# 3) Add tracking and reporting methods

import simpy
from collections import defaultdict



class QueueCount(object):
    def __init__(self, env, initial_count=0):
        self.count = initial_count
        self.env = env
        self.last_time = env.now
        self.time_records = {}
    def add(self):
        self.update_tracking(self.count + 1)

    def update_tracking(self, new_count):
        delta_t = self.env.now - self.last_time
        self.time_records[self.count] = self.time_records.get(self.count, 0) + delta_t

        self.count = new_count
        self.last_time = self.env.now

    def remove(self):
        self.update_tracking(self.count - 1)


class MonitoredStore(simpy.Store):
    def __init__(self, env, capacity=float('inf')):
        super(MonitoredStore, self).__init__(env, capacity)

        self._last_value = len(self.items)
        self._cumulative_item_rec = []
        self._cumulative_time_rec = []

        self.reset_tracking()

    # simpy.Store._do_put method override
    def _do_put(self, event):
        if len(self.items) < self._capacity:
            self.items.append(event.item)
            event.succeed()
            self._update_tracking()

    # simpy.Store._do_get method override
    def _do_get(self, event):
        if self.items:
            event.succeed(self.items.pop(0))
            self._update_tracking()

    def reset_tracking(self):
        self._last_reset = self._env.now
        self._last_time = self._env.now
        self._weighted_items = 0.0

        self._item_rec = []
        self._time_rec = []
        self._item_time_dict = defaultdict(int)
        self._item_time_dict[self._last_value] = 0
        self._update_tracking()

    def _update_tracking(self):
        if self._env.now > self._last_time or len(self._item_rec) == 0:
            time_delta = self._env.now - self._last_time
            self._weighted_items += time_delta * float(self._last_value)
            self._item_rec.append(self._last_value)
            self._time_rec.append(time_delta)
            self._item_time_dict[self._last_value] += time_delta
        self._last_value = len(self.items)
        self._last_time = self._env.now
        if len(self._cumulative_item_rec) == 0:
            self._cumulative_item_rec.append(self._last_value)
            self._cumulative_time_rec.append(self._last_time)
        else:
            if self._last_time != self._cumulative_time_rec[-1]:
                self._cumulative_item_rec.append(self._cumulative_item_rec[-1])
                self._cumulative_time_rec.append(self._last_time)
                self._cumulative_item_rec.append(self._last_value)
                self._cumulative_time_rec.append(self._last_time)
            else:
                self._cumulative_item_rec.pop(-1)
                self._cumulative_item_rec.append(self._last_value)

    @property
    def avg_value(self):
        try:
            if self._env.now > self._time_rec[-1]:
                self._update_tracking()
        except Exception:
            self._update_tracking()

        time_delta = float(self._env.now - self._last_reset)
        if time_delta == 0:
            time_delta = 1

        return sum(x * y for (x, y) in zip(self._time_rec, self._item_rec)) / time_delta

    @property
    def time_series(self):
        self._update_tracking()
        string = 'Time\tValue\n'
        for time, value in zip(self._cumulative_time_rec, self._cumulative_item_rec):
            string += '%f\t%d\n' % (time, value)

        return string

    def print_stats(self):
        self._update_tracking()
        total = float(sum(list(self._item_time_dict.values())))
        if total == 0:
            total = 1
        avg = 0.0
        for index, key in enumerate(sorted(self._item_time_dict.keys())):
            print('%d -> %f%%' % (key, 100 * self._item_time_dict[key] / total))
            avg += key * self._item_time_dict[key] / total
        print('Weighted Avg: %f' % avg)
        print('Cumulated Avg: %f' % self.avg_value)


class MonitoredFilterStore(simpy.FilterStore, MonitoredStore):
    def __init__(self, env, capacity=float('inf')):
        super(MonitoredFilterStore, self).__init__(env, capacity)

        self._last_value = len(self.items)
        self._cumulative_item_rec = []
        self._cumulative_time_rec = []

        self.reset_tracking()

    # simpy.FilterStore._do_get method override
    def _do_get(self, event):
        for item in self.items:
            if event.filter(item):
                self.items.remove(item)
                event.succeed(item)
                break

        self._update_tracking()

        return True


if __name__ == '__main__':
    q = MonitoredStore(simpy.Environment())
    q.print_stats()

    p = MonitoredFilterStore(simpy.Environment())
    p.print_stats()
