import time
import requests
from typing import Optional

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36 auto-sns-digest/0.1"
)


def get(url: str, *, timeout: int = 20, headers: Optional[dict] = None,
        retries: int = 2, backoff: float = 1.5) -> Optional[requests.Response]:
    h = {"User-Agent": UA, "Accept-Language": "en,ja;q=0.8"}
    if headers:
        h.update(headers)
    last_err = None
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, headers=h, timeout=timeout)
            if r.status_code == 200:
                return r
            if r.status_code in (429, 500, 502, 503, 504) and attempt < retries:
                time.sleep(backoff * (attempt + 1))
                continue
            return r
        except requests.RequestException as e:
            last_err = e
            if attempt < retries:
                time.sleep(backoff * (attempt + 1))
                continue
    if last_err:
        print(f"[http] giving up on {url}: {last_err}")
    return None
