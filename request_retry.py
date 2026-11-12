import time

import requests


RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


def get_with_retries(
    url,
    *,
    attempts=4,
    timeout=(10, 90),
    backoff_seconds=5,
    request_get=requests.get,
    sleep=time.sleep,
    **kwargs,
):
    """GET an HTTP resource with bounded retries for transient failures."""
    if attempts < 1:
        raise ValueError("attempts must be at least 1")

    for attempt in range(1, attempts + 1):
        try:
            response = request_get(url, timeout=timeout, **kwargs)
            response.raise_for_status()
            return response
        except (requests.Timeout, requests.ConnectionError) as exc:
            retryable = True
            last_error = exc
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            retryable = status in RETRYABLE_STATUS_CODES
            last_error = exc

        if not retryable or attempt == attempts:
            raise last_error

        delay = backoff_seconds * (2 ** (attempt - 1))
        print(
            f"Transient HTTP failure on attempt {attempt}/{attempts}: {last_error}. "
            f"Retrying in {delay} seconds."
        )
        sleep(delay)

