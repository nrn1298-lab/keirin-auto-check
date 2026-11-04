import io
import re
import sys
from collections import defaultdict
from contextlib import redirect_stdout
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from keirin_filter import check_live_race, extract_array

BASE = "https://www.keibure.com/"
TODAY = datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y%m%d")

RACE_RE = re.compile(r"^/(\d{1,3})/(20\d{6})/(\d{1,2})/?$")
HTML_RACE_RE = re.compile(
    r"(?:https?://(?:www\.)?keibure\.com)?/\d{1,3}/20\d{6}/\d{1,2}(?:[/?#][^\s\"'<>]*)?"
)

LATE_CUTOFF = 20 * 60 + 40

VENUE_NAMES = {
    11: "函館", 12: "青森", 13: "いわき平",
    21: "弥彦", 22: "前橋", 23: "取手",
    24: "宇都宮", 25: "大宮", 26: "西武園",
    27: "京王閣", 28: "立川",
    31: "松戸", 32: "千葉", 34: "川崎",
    35: "平塚", 36: "小田原", 37: "伊東温泉",
    38: "静岡",
    42: "名古屋", 43: "岐阜", 44: "大垣",
    45: "豊橋", 46: "富山", 47: "松阪",
    48: "四日市",
    51: "福井", 53: "奈良", 54: "向日町",
    55: "和歌山", 56: "岸和田",
    61: "玉野", 62: "広島", 63: "防府",
    71: "高松", 73: "小松島",
    74: "高知", 75: "松山",
    81: "小倉", 83: "久留米", 84: "武雄",
    85: "佐世保", 86: "別府", 87: "熊本",
}


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.text_parts = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)

    def handle_data(self, data):
        self.text_parts.append(data)


def fetch(url):
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=25) as response:
        return response.read().decode("utf-8", errors="replace")


def discover():
    queue = [BASE]
    visited = set()
    races = {}

    while queue and len(visited) < 40:
        page = queue.pop(0)

        if page in visited:
            continue

        visited.add(page)

        try:
            html = fetch(page)
        except Exception as exc:
            if page == BASE:
                raise RuntimeError(
                    f"開催一覧の取得失敗: {exc}"
                ) from exc

            print(f"INDEX WARNING: {page}: {exc}")
            continue

        parser = PageParser()
        parser.feed(html)

        candidates = parser.links + HTML_RACE_RE.findall(html)

        for candidate in candidates:
            url = urljoin(page, candidate).split("#", 1)[0]
            parsed = urlparse(url)

            if parsed.hostname not in (
                "keibure.com",
                "www.keibure.com"
            ):
                continue

            match = RACE_RE.fullmatch(parsed.path)

            if match and match.group(2) == TODAY:
                venue = int(match.group(1))
                race_no = int(match.group(3))

                if 1 <= race_no <= 12:
                    races[(venue, race_no)] = (
                        f"https://www.keibure.com/"
                        f"{venue}/{TODAY}/{race_no}"
                    )

            elif TODAY in url and url not in visited and url not in queue:
                queue.append(url)

    if not races:
        raise RuntimeError(
            "ケイブレの当日レースURLが見つかりません"
        )

    return races


def get_deadline(html):
    parser = PageParser()
    parser.feed(html)

    visible = " ".join(parser.text_parts)

    match = re.search(
        r"締切\s*(\d{1,2}):(\d{2})",
        visible
    )

    if not match:
        return None

    hour, minute = map(int, match.groups())

    if hour > 23 or minute > 59:
        return None

    return hour * 60 + minute


def format_match(venue, race_no, url, html):
    venue_name = VENUE_NAMES.get(
        venue,
        f"競輪場コード{venue}"
    )

    lines = [
        "================================",
        "【条件一致レース発見！】",
        f"開催場：{venue_name}競輪場",
        f"レース：{race_no}R",
    ]

    try:
        riders = extract_array(html, "__ents")
        lineup = extract_array(html, "__comp")

        groups = [
            str(item["cars"]).split("-")
            for item in lineup
        ]

        lineup_text = "・".join(
            "-".join(group)
            for group in groups
        )

        scores = {
            str(r["car_no"]): float(r["tokuten"])
            for r in riders
        }

        lines.append(f"並び：{lineup_text}")

        lines.append(
            f"競走得点："
            f"1番車 {scores['1']:.2f} / "
            f"6番車 {scores['6']:.2f} / "
            f"4番車 {scores['4']:.2f}"
        )

    except Exception as exc:
        lines.append(
            f"詳細：取得できませんでした"
            f"（{type(exc).__name__}）"
        )

    lines.append(f"出走表URL：{url}")
    lines.append("================================")

    return "\n".join(lines)


def main():
    print(f"Checking races for {TODAY}")

    races = discover()

    by_venue = defaultdict(list)

    for venue, race_no in races:
        by_venue[venue].append(race_no)

    pages = {}
    deadlines = {}
    errors = []

    for key, url in sorted(races.items()):
        try:
            html = fetch(url)
            pages[key] = html
            deadlines[key] = get_deadline(html)

        except Exception as exc:
            errors.append(
                f"{url}: {type(exc).__name__}: {exc}"
            )

    midnight_venues = set()

    for venue, race_numbers in by_venue.items():

        late_count = sum(
            1 for race_no in race_numbers
            if deadlines.get((venue, race_no)) is not None
            and deadlines[(venue, race_no)] >= LATE_CUTOFF
        )

        if max(race_numbers) <= 7 and late_count >= 2:
            midnight_venues.add(venue)

    checked = 0
    excluded = []
    missing_data = []
    matches = []

    for (venue, race_no), url in sorted(races.items()):

        if venue in midnight_venues:
            excluded.append(url)
            continue

        if (venue, race_no) not in pages:
            continue

        try:
            with redirect_stdout(io.StringIO()):
                matched = check_live_race(url)

            checked += 1

            if matched:
                detail = format_match(
                    venue,
                    race_no,
                    url,
                    pages[(venue, race_no)]
                )

                matches.append(detail)

        except ValueError as exc:

            if "__ents not found" in str(exc):
                missing_data.append(url)
            else:
                errors.append(f"{url}: {exc}")

        except Exception as exc:
            errors.append(
                f"{url}: {type(exc).__name__}: {exc}"
            )

    print("\n========== RESULTS ==========")
    print(f"Date: {TODAY}")
    print(f"Discovered venues: {len(by_venue)}")
    print(f"Discovered URLs: {len(races)}")
    print(f"Midnight venue candidates: {sorted(midnight_venues)}")
    print(f"Midnight races excluded: {len(excluded)}")
    print(f"Checked: {checked}")
    print(f"Pages without rider data: {len(missing_data)}")
    print(f"Other errors: {len(errors)}")
    print(f"Matches: {len(matches)}")

    if matches:
        print("\n========== MATCH DETAILS ==========")

        for detail in matches:
            print(detail)

    for url in missing_data:
        print(f"NO RIDER DATA: {url}")

    for error in errors:
        print(f"FETCH ERROR: {error}")

    if missing_data or errors:
        raise SystemExit(
            f"INCOMPLETE SCAN: {len(missing_data)} "
            f"pages without rider data, "
            f"{len(errors)} other errors"
        )


if __name__ == "__main__":
    main()
