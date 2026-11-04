"""Discover today's keibure race links and check the existing keirin rule."""
import re
import sys
import io
from contextlib import redirect_stdout
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from keirin_filter import check_live_race

BASE = "https://www.keibure.com/"
TODAY = datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y%m%d")
RACE_RE = re.compile(r"/(?P<venue>\d{1,3})/(?P<date>20\d{6})/(?P<race>\d{1,2})(?:[/?#]|$)")


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self.links.append(href)


def fetch(url):
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=25) as response:
        return response.read().decode("utf-8", errors="replace")


def same_site(url):
    return urlparse(url).hostname in {"keibure.com", "www.keibure.com"}


def discover_races():
    """Read the site's own index and date-linked pages, not a fixed venue list."""
    queue = [BASE]
    seen = set()
    races = {}
    while queue and len(seen) < 30:
        page = queue.pop(0)
        if page in seen:
            continue
        seen.add(page)
        try:
            html = fetch(page)
        except Exception as exc:
            if page == BASE:
                raise RuntimeError(f"Cannot load keibure index: {exc}") from exc
            print(f"INDEX WARNING: {page}: {exc}", file=sys.stderr)
            continue
        parser = Links()
        parser.feed(html)
        candidates = parser.links + re.findall(
            r'(?:https?://(?:www\.)?keibure\.com)?/\d{1,3}/20\d{6}/\d{1,2}(?:[/?#][^\s"\'<>]*)?',
            html,
        )
        for candidate in candidates:
            url = urljoin(page, candidate).split("#", 1)[0]
            if not same_site(url):
                continue
            m = RACE_RE.search(urlparse(url).path)
            if m and m.group("date") == TODAY:
                venue = int(m.group("venue"))
                race_no = int(m.group("race"))
                if 1 <= race_no <= 12:
                    canonical = f"https://www.keibure.com/{venue}/{TODAY}/{race_no}"
                    races[(venue, race_no)] = canonical
            elif TODAY in url and url not in seen and url not in queue:
                queue.append(url)
    if not races:
        raise RuntimeError(
            "No today's race links found on keibure; index layout may have changed. "
            "Not treating this as zero matches."
        )
    return races


def main():
    print(f"Checking races for {TODAY}")
    races = discover_races()
    print(f"Discovered: {len(races)} race links in {len({v for v, _ in races})} venues")
    checked = 0
    errors = 0
    matches = []
    for (venue, race_no), url in sorted(races.items()):
        try:
            with redirect_stdout(io.StringIO()):
                matched = check_live_race(url)
            checked += 1
            if matched:
                matches.append((venue, race_no, url))
        except Exception as exc:
            errors += 1
            print(f"FETCH ERROR venue {venue} {race_no}R: {type(exc).__name__}: {exc}")

    print("\n========== RESULTS ==========")
    print(f"Date: {TODAY}")
    print(f"Checked: {checked}")
    print(f"Errors: {errors}")
    print(f"Matches: {len(matches)}")
    for venue, race_no, url in matches:
        print(f"Venue code {venue} {race_no}R {url}")
    if errors:
        raise SystemExit(f"INCOMPLETE SCAN: {errors} race pages failed")


if __name__ == "__main__":
    main()
