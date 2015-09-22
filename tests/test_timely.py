import boto.ec2
import datetime
import unittest

from time import sleep
from timely import Timely


class TimelyTestCase(unittest.TestCase):
    def setUp(self):
        self.timely = Timely(verbose=True)
        self.conn = boto.ec2.connect_to_region('us-east-1')
        self.now = datetime.datetime.now()

    def test_times_tag_is_created(self):
        self.timely.set(weekdays=['*'])
        instances = self.conn.get_only_instances()
        for instance in instances:
            if instance.state != 'terminated':
                self.assertIn('times', instance.tags)
            else:
                continue

    def test_times_tag_has_length_of_7(self):
        self.timely.set(weekdays=['*'])
        instances = self.conn.get_only_instances()
        for instance in instances:
            # Ensure that the length of the `times` list object has a length
            # of 7
            times = instance.tags['times'].split(';')
            self.assertEqual(len(times), 7)

    def test_time_is_set_for_weekday(self):
        weekday = self.timely.weekdays[self.now.weekday()]
        self.timely.set(weekdays=[weekday], start_time='9:00 AM',
                        end_time='5:00 PM')
        instances = self.conn.get_only_instances()
        for instance in instances:
            times = instance.tags['times'].split(';')
            self.assertNotEqual(times[self.now.weekday()], str(None))

    def test_exception_if_start_time_is_greater_than_equal_to_end_time(self):
        with self.assertRaises(ValueError):
            # Greater
            self.timely.set(weekdays=['*'], start_time='9:00 AM',
                            end_time='8:00 AM')
            # Equal
            self.timely.set(weekdays=['*'], start_time='9:00 AM',
                            end_time='9:00 AM')

    def test_unset_method(self):
        self.timely.set(weekdays=['*'], start_time='9:00 AM',
                        end_time='5:00 PM')
        try:
            instance = self.conn.get_only_instances()[0]
            times = self.timely.all()[instance.id]
            # First - set times for all days of the week
            self.assertEqual(len(times), 7)
            # Second - unset times for all days of the week
            self.timely.unset(weekdays=['*'])
            times = self.timely.all()[instance.id]
            self.assertEqual(len(times), 0)
        except IndexError:
            pass

    def test_check_method_stops_instance_if_should_not_be_running(self):
        try:
            instance = self.conn.get_only_instances()[0]
            if instance.state == 'stopped':
                # Start the instance to ensure it is running
                instance.start()
            weekday = self.timely.weekdays[self.now.weekday()]
            # Automatically sets `start_time` and `end_time` to `None`
            self.timely.set(weekdays=[weekday])
            # Ensure that the instance is being stopped
            self.timely.check()
            stopped = False
            instance = None
            while not stopped:
                try:
                    # Need to remake a connection to AWS to get the updated
                    # instance status
                    instance = self.conn.get_only_instances()[0]
                    if instance.state == 'stopped':
                        stopped = True
                    else:
                        sleep(1)
                except IndexError:
                    pass
            self.assertEqual(instance.state, 'stopped')
        except IndexError:
            pass

    def tearDown(self):
        del self.timely
