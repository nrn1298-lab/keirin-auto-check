from urllib.request import Request, urlopen
from html.parser import HTMLParser
import re

URL = "https://www.keibure.com/42/20261101/1"

class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip and data.strip():
            self.parts.append(data.strip())

req = Request(URL, headers={"User-Agent": "Mozilla/5.0"})
with urlopen(req, timeout=20) as response:
    html = response.read().decode("utf-8", errors="replace")
    print("HTTP:", response.status)

parser = TextExtractor()
parser.feed(html)
text = " ".join(parser.parts)
text = re.sub(r"\s+", " ", text)

for word in ("競走得点", "並び", "出走表"):
    print("\n=== " + word + " ===")
    matches = list(re.finditer(re.escape(word), text))
    print("Occurrences:", len(matches))
    for match in matches[:4]:
        start = max(0, match.start() - 120)
        end = min(len(text), match.end() + 600)
        print(text[start:end])
        print("---")
