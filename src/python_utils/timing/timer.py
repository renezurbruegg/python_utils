"""Sub-module for a timer class that can be used for performance measurements."""

from __future__ import annotations

import math
import time
from contextlib import ContextDecorator
from typing import Any

from python_utils.misc import Throttle

_global_timer_manager = None


def get_global_timer_manager(throttle: float = 1.0, unit="ms", scale=1e3):
    """Returns a global timer manager which can be used to time multiple events.

    This function is useful when you want to time multiple functions across multiple files.
    It is a singleton, so it will return the same instance every time after the first call.

    Note that the arguments are only used for the first call. Subsequent calls will ignore the arguments.

    Args:
        throttle: The interval [s] at which to print the message.
            Defaults to 1.0, which means the message will be printed
            every second.
        unit: The unit to use for printing the time. Defaults to "ms".
        scale: The scale to use for printing the time. Defaults to 1e3.

    Example:
        .. code-block:: python
        from omni.isaac.orbit.utils.timer import get_global_timer_manager

        timer_manager = get_global_timer_manager()
        with timer_manager("timer1"):
            # do something
            pass

            with timer_manager("timer2"):
                # do something else
                pass

        with timer_manager("timer3"):
            # do something else
            pass

        # Output:
        # timer1: 0.0000 ms - Avg: 0.0000 ms - FPS: 0.0000
        #     timer2: 0.0000 ms - Avg: 0.0000 ms - FPS: 0.0000
        # timer3: 0.0000 ms - Avg: 0.0000 ms - FPS: 0.0000

    """
    global _global_timer_manager
    if _global_timer_manager is None:
        _global_timer_manager = TimerManager(throttle, unit, scale)
    return _global_timer_manager


class GlobalTimer:
    def __init__(self, name: str, throttle: float = 1.0, unit="ms", scale=1e3, **kwargs):
        self._manager = get_global_timer_manager(throttle, unit, scale, **kwargs)
        self._timer = self._manager(name)
        self._name = name

    def start(self, *args, **kwargs):
        self._manager.start(self._name, *args, **kwargs)

    def stop(self, *args, **kwargs):
        self._manager.stop(self._name, *args, **kwargs)

    def __call__(self, *args, **kwargs):
        return self._manager(*args, **kwargs)
    
    def __getitem__(self, *args, **kwargs):
        return self._manager.__getitem__(*args, **kwargs)
    
    def __enter__(self, *args, **kwargs):
        return self._manager.__enter__(*args, **kwargs)
    
    def __exit__(self, *args, **kwargs):
        return self._manager.__exit__(*args, **kwargs)
    

class TimerError(Exception):
    """A custom exception used to report errors in use of :class:`Timer` class."""

    pass


class TimerManager:
    """A class to keep track of time for performance measurement over multiple iterations.

    This class is useful when you want to time multiple function multiple times and also print the average time.

    It uses the `time.perf_counter` function to measure time.

    Args:
        throttle: The interval [s] at which to print the message.
            Defaults to 1.0, which means the message will be printed
            every second.
        unit: The unit to use for printing the time. Defaults to "ms".
        scale: The scale to use for printing the time. Defaults to 1e3.

    Example:
        .. code-block:: python
        from omni.isaac.orbit.utils.timer import TimerManager
        manager = TimerManager()
        for i in range(10):
            with manager("function1"):
                # do something
                pass
            with manager("function2"):
                # do something else
                pass

        # Output:
        # function1: 0.0000 ms - Avg: 0.0000 ms - FPS: 0.0000
        # function2: 0.0000 ms - Avg: 0.0000 ms - FPS: 0.0000
    """

    def __init__(self, throttle: float = 1.0, unit="s", scale=1.0):
        self._timers: dict[str, Timer] = {}
        self._throttles = {}
        self._interval = throttle
        self._active_timer_name = None
        self._unit = unit
        self._scale = scale

        self._call_stack = []

    def start(self, name: str):
        """Start an internal timer with the given name. If the timer does not exist, it will be created."""
        if name not in self._timers:
            self._create_timer(name)
        self._timers[name].start()

    def _create_timer(self, name: str, throttle: float = None, unit=None, scale=None):
        """Internal function to create a timer with the given name.

        Args:
            name: The name of the timer to create.
            throttle: The interval [s] at which to print the message.
                Defaults to 1.0, which means the message will be printed
                every second.
            unit: The unit to use for printing the time. Defaults to "ms".
            scale: The scale to use for printing the time. Defaults to 1e3.
        """
        if name not in self._timers:
            if throttle is None:
                throttle = self._interval
            if unit is None:
                unit = self._unit
            if scale is None:
                scale = self._scale

            self._timers[name] = Timer(name, throttle, unit, scale)
            self._throttles[name] = Throttle(self._interval)

    def stop(self, name: str, indent: int = 0):
        """Stop the internal timer with the given name and print the statistics.

        If the timer does not exist, an error will be raised.

        Args:
            name: The name of the timer to stop.
            indent: The number of tabs to indent the message. Defaults to 0.
        """
        if name not in self._timers:
            raise TimerError(f"Timer {name} not found.")
        self._timers[name].stop()

        self._throttles[name].rate_limit(lambda ind=indent: self._timers[name].print(ind))

    def __call__(self, name: str, throttle: float = None, unit=None, scale=None):
        """Start a timer with the given name and return this `TimerManager` instance.

        Args:
            name: The name of the timer to start.
            throttle: The interval [s] at which to print the message.
                Defaults to 1.0, which means the message will be printed
                every second.
            unit: The unit to use for printing the time. Defaults to "ms".
            scale: The scale to use for printing the time. Defaults to 1e3.

        Returns:
            This `TimerManager` instance.
        """
        if name not in self._timers:
            self._create_timer(name, throttle, unit, scale)
        self._active_timer_name = name
        return self

    def __getitem__(self, name: str) -> Timer:
        """Return the timer with the given name.

        Raises an error if the timer does not exist.

        Args:
            name: The name of the timer to get.

        Returns:
            The timer with the given name.
        """
        return self._timers[name]

    def __enter__(self):
        """Context manager to start the timer with the given name."""
        if self._active_timer_name is None:
            raise TimerError("No active timer. Please use with timer(''name') for this context manager.")
        self.start(self._active_timer_name)
        # Note we create a call stack to handle nested context managers
        self._call_stack.append(self._active_timer_name)
        return self

    def __exit__(self, *exc_info: Any):
        """Context manager to stop the timer with the given name."""
        # pop from call stack to handle nested context managers
        timer_name = self._call_stack.pop()
        self.stop(timer_name, indent=len(self._call_stack))
        self._active_timer_name = self._call_stack[-1] if len(self._call_stack) > 0 else None


class Timer(ContextDecorator):
    """A timer for performance measurements.

    A class to keep track of time for performance measurement.
    It allows timing via context managers and decorators as well.

    It uses the `time.perf_counter` function to measure time. This function
    returns the number of seconds since the epoch as a float. It has the
    highest resolution available on the system.

    As a regular object:

    .. code-block:: python

        import time

        from omni.isaac.orbit.utils.timer import Timer

        timer = Timer()
        timer.start()
        time.sleep(1)
        print(1 <= timer.time_ela
        psed <= 2)  # Output: True

        time.sleep(1)
        timer.stop()
        print(2 <= stopwatch.total_run_time)  # Output: True

    As a context manager:

    .. code-block:: python

        import time

        from omni.isaac.orbit.utils.timer import Timer

        with Timer() as timer:
            time.sleep(1)
            print(1 <= timer.time_elapsed <= 2)  # Output: True

    Reference: https://gist.github.com/sumeet/1123871
    """

    def __init__(self, msg: str | None = None, print_interval: float = 1.0, unit="s", scale=1.0, warmup=100):
        """Initializes the timer.

        Args:
            msg: The message to display when using the timer
                class in a context manager. Defaults to None.
            print_interval: The interval [s] at which to print the message.
                Defaults to 1.0, which means the message will be printed
                every second.
            unit: The unit to use for printing the time. Defaults to "ms".
            scale: The scale to use for printing the time. Defaults to 1e3.
            warmup: The number of samples to ignore before recording statistics.
        """
        self._msg = msg
        self._start_time = None
        self._stop_time = None
        self._elapsed_time = None
        self._unit = unit
        self._scale = scale
        self._print_interval = print_interval
        self._warmup = warmup

        # Record average statistics
        self._total_elapsed_time = 0
        self._sum_elapsed_time_squared = 0

        self._n_samples = 0
        #
        self._throttle = Throttle(self._print_interval)

    """
    Properties
    """

    @property
    def time_elapsed(self) -> float:
        """The number of seconds that have elapsed since this timer started timing.

        Note:
            This is used for checking how much time has elapsed while the timer is still running.
        """
        return time.perf_counter() - self._start_time

    @property
    def total_run_time(self) -> float:
        """The number of seconds that elapsed from when the timer started to when it ended."""
        return self._elapsed_time

    @property
    def mean_elapsed_time(self) -> float:
        """The average elapsed time."""
        return self._total_elapsed_time / self._n_samples

    @property
    def std_elapsed_time(self) -> float:
        """The standard deviation of the elapsed time."""
        return math.sqrt(self._sum_elapsed_time_squared / self._n_samples - self.mean_elapsed_time**2)

    @property
    def num_calls(self) -> int:
        """The number of times the timer was called."""
        return self._n_samples

    """
    Operations
    """

    def start(self):
        """Start timing."""
        if self._start_time is not None:
            raise TimerError("Timer is running. Use .stop() to stop it")

        self._start_time = time.perf_counter()

    def stop(self):
        """Stop timing."""
        if self._start_time is None:
            raise TimerError("Timer is not running. Use .start() to start it")

        self._stop_time = time.perf_counter()
        self._elapsed_time = self._stop_time - self._start_time
        self._start_time = None

        if self._n_samples == self._warmup:
            # Record average statistics
            self._n_samples = 0
            self._warmup = 0
            self._total_elapsed_time = 0
            self._sum_elapsed_time_squared = 0

        self._n_samples += 1
        self._total_elapsed_time += self._elapsed_time
        self._sum_elapsed_time_squared += self._elapsed_time**2

    def prints(self):
        """Print the current statistics."""

        output = f"{self._msg}: {self._scale * self._elapsed_time:0.6f} {self._unit}"

        if self._n_samples > 1:
            mean = self._scale * self.mean_elapsed_time
            std = self._scale * self.std_elapsed_time
            output += f"- Avg: {mean:0.6f}{self._unit} +/- {std:0.6f}{self._unit}"
            output += f" - Fps: {self._n_samples / self._total_elapsed_time:0.2f}"
        return output

    def print(self, indent: int = 0):
        """Print the current statistics."""
        print("\t" * indent, self.prints())

    def __str__(self) -> str:
        """A string representation of the timer.

        Contains the last elapsed time and the average elapsed time.

        Returns:
            A string containing the elapsed time.
        """
        return self.prints()

    """
    Context managers
    """

    def __enter__(self) -> Timer:
        """Start timing and return this `Timer` instance."""
        self.start()
        return self

    def __exit__(self, *exc_info: Any):
        """Stop timing."""
        self.stop()
        # print message
        if self._msg is not None:
            self._throttle.rate_limit(self.print)