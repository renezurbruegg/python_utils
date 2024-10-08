# Copyright (c) 2022-2024, The ORBIT Project Developers.
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import annotations

import time
import unittest

from python_utils.timing import Timer, TimerManager, get_global_timer_manager


class TestTimer(unittest.TestCase):
    """Test fixture for the Timer class."""

    def setUp(self):
        # number of decimal places to check
        self.precision_places = 2

    def test_timer_as_object(self):
        """Test using a `Timer` as a regular object."""
        timer = Timer()
        timer.start()
        self.assertAlmostEqual(0, timer.time_elapsed, self.precision_places)
        time.sleep(1)
        self.assertAlmostEqual(1, timer.time_elapsed, self.precision_places)
        timer.stop()
        self.assertAlmostEqual(1, timer.total_run_time, self.precision_places)

    def test_timer_as_context_manager(self):
        """Test using a `Timer` as a context manager."""
        with Timer() as timer:
            self.assertAlmostEqual(0, timer.time_elapsed, self.precision_places)
            time.sleep(1)
            self.assertAlmostEqual(1, timer.time_elapsed, self.precision_places)


class TestTimerManager(unittest.TestCase):
    def setUp(self):
        # number of decimal places to check
        self.precision_places = 2

    def test_timer_manager(self):
        """Test using a `TimerManager` as a context manager."""
        manager = TimerManager()
        with manager("test1"):
            time.sleep(1)
        with manager("test2"):
            time.sleep(2)

        self.assertAlmostEqual(1, manager["test1"].total_run_time, self.precision_places)
        self.assertAlmostEqual(2, manager["test2"].total_run_time, self.precision_places)

        # Time multiple calls
        for i in range(100):
            with manager("loop"):
                time.sleep(0.01)

        self.assertAlmostEqual(0.01, manager["loop"].mean_elapsed_time, self.precision_places)
        self.assertAlmostEqual(0.0001, manager["loop"].std_elapsed_time, self.precision_places)

    def test_nested_managers(self):
        """Test using nested `TimerManager`s as context managers."""
        manager = TimerManager()
        with manager("test1"):
            time.sleep(1)
            with manager("test2"):
                time.sleep(2)

        self.assertAlmostEqual(2, manager["test2"].total_run_time, self.precision_places)
        self.assertAlmostEqual(3, manager["test1"].total_run_time, self.precision_places)

    def test_global_manager(self):
        """Test using the global `TimerManager`."""
        mgr = get_global_timer_manager()
        with mgr("test"):
            time.sleep(0.1)
        self.assertAlmostEqual(0.1, mgr["test"].total_run_time, self.precision_places)
        with mgr("test"):
            time.sleep(0.1)
        self.assertAlmostEqual(0.1, mgr["test"].total_run_time, self.precision_places)
        self.assertEqual(2, mgr["test"].num_calls)


if __name__ == "__main__":
    unittest.main()