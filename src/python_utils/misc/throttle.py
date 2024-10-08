"""General Purpose Utilities."""

import time
from functools import wraps
from typing import Callable


class Throttle:
    """Decorator or Class that prevents a function from being called more than once every time period.

    Use this to rate-limit the function calls. This is useful for logging, where you may want to log
    at a certain rate, but not every time the function is called.

    Example:
    As decorator:

    .. code-block:: python
        @Throttle(1.0)
        def foo():
            print("foo")
        for _ in range(100):
            foo()
            time.sleep(0.1)

        # --> prints "foo" once every second



    As class:
    .. code-block:: python
        throttle = Throttle(1.0)
        for _ in range(100):
            throttle.rate_limit(lambda: print("foo"))
            time.sleep(0.1)

        # --> prints "foo" once every second
    """

    def __init__(self, throttle_period: float = 0):
        """Initializes the class

        Args:
            throttle_period: The time period [s] to throttle the function call. Defaults to 0."""
        self._throttle_period = throttle_period
        self._time_of_last_call = 0

    def rate_limit(self, func: Callable, *args, **kwargs) -> None:
        """Prevents a function from being called more than once every time period.

        Args:
            func: The function to throttle.
            args: The arguments to pass to the function.
            kwargs: The keyword arguments to pass to the function.
        """
        now = time.time()
        time_since_last_call = now - self._time_of_last_call
        if time_since_last_call > self._throttle_period:
            self._time_of_last_call = now
            func(*args, **kwargs)

    def __call__(self, func: Callable) -> Callable:
        """Prevents a function from being called more than once every time period.

        This should be used as a decorator. The annotated function will be throttled, meaning that additional
        calls to the function will be ignored until the throttle period has expired. This allows for
        rate-limiting of functions, e.g. for logging.

        Args:
            func: The function to throttle.

        Returns:
            The wrapped function.
        """

        @wraps(func)
        def wrapper(*args, **kwargs):
            return self.rate_limit(func, *args, **kwargs)

        return wrapper