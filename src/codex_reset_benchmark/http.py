from __future__ import annotations

from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import urllib.robotparser

USER_AGENT = "codex-reset-benchmark/0.1 (+https://github.com/AghDoo/codex-reset-benchmark)"


class FetchError(RuntimeError):
    pass


class AccessDenied(FetchError):
    pass


@dataclass
class HttpResponse:
    url: str
    status: int
    text: str


class HttpClient:
    def __init__(self, timeout: float = 20.0, max_bytes: int = 1_000_000):
        self.timeout = timeout
        self.max_bytes = max_bytes

    def _request(self, url: str) -> HttpResponse:
        request = Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json,text/html;q=0.9,text/plain;q=0.8,*/*;q=0.5",
                "Cache-Control": "no-cache",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:  # noqa: S310 - public configured URLs only
                status = int(getattr(response, "status", 200))
                data = response.read(self.max_bytes + 1)
                if len(data) > self.max_bytes:
                    raise FetchError(f"response exceeds {self.max_bytes} bytes")
                charset = response.headers.get_content_charset() or "utf-8"
                return HttpResponse(response.geturl(), status, data.decode(charset, errors="replace"))
        except HTTPError as exc:
            if exc.code in {401, 403, 429}:
                raise AccessDenied(f"HTTP {exc.code} from {url}; collector will not bypass access controls") from exc
            raise FetchError(f"HTTP {exc.code} from {url}") from exc
        except URLError as exc:
            raise FetchError(f"network error for {url}: {exc.reason}") from exc

    def robots_allowed(self, url: str) -> bool:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        request = Request(robots_url, headers={"User-Agent": USER_AGENT, "Accept": "text/plain,*/*;q=0.1"})
        try:
            with urlopen(request, timeout=self.timeout) as response:  # noqa: S310
                data = response.read(min(self.max_bytes, 256_000)).decode("utf-8", errors="replace")
        except HTTPError as exc:
            if exc.code == 404:
                return True
            if exc.code in {401, 403}:
                return False
            raise FetchError(f"cannot evaluate robots.txt for {url}: HTTP {exc.code}") from exc
        except URLError as exc:
            raise FetchError(f"cannot evaluate robots.txt for {url}: {exc.reason}") from exc

        parser = urllib.robotparser.RobotFileParser()
        parser.set_url(robots_url)
        parser.parse(data.splitlines())
        return parser.can_fetch(USER_AGENT, url)

    def get(self, url: str, *, respect_robots: bool = True) -> HttpResponse:
        if respect_robots and not self.robots_allowed(url):
            raise AccessDenied(f"robots.txt disallows collection of {url}")
        return self._request(url)
