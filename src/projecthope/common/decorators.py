import functools
import time


def timer(func):
    """Print the runtime of the decorated function"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        value = func(*args, **kwargs)
        end_time = time.perf_counter()
        run_time = end_time - start_time
        print(f"Finished {func.__name__!r} in {run_time:.6f} secs")

        return value

    return wrapper


def count_func_calls(func):
    """Counts the number of function calls."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        wrapper.calls += 1
        value = func(*args, **kwargs)

        return value

    wrapper.calls = 0

    return wrapper
