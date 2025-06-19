import time
from functools import wraps

def timed_cache(timeout: int = 60):
    """Decorator to cache function result for a given timeout (in seconds)."""
    def decorator(func):
        cache = {}
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            now = time.time()
            key = (args, tuple(sorted(kwargs.items())))
            if key in cache:
                result, timestamp = cache[key]
                if now - timestamp < timeout:
                    return result
            result = func(self, *args, **kwargs)
            cache[key] = (result, now)
            return result
        return wrapper
    return decorator 