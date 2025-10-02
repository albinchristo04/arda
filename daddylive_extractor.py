import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from dateutil import parser
from datetime import datetime, timedelta
import json
import re

class DaddyliveExtractor:
    def __init__(self):
        self.domain = "daddylivestream.com"
        self.base_url = f"https://{self.domain}"
        self.timeout = 15
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        })

    def parse_header(self, header, time):
        timestamp = parser.parse(header[:header.index("-")] + " " + time)
        timestamp = timestamp.replace(year=2024)  # fix incorrect year
        return timestamp

    def resolve_m3u8(self, page_url):
        """Take a stream page (e.g. /stream/stream-123.php), return final m3u8 with headers"""
        try:
            r = self.session.get(page_url, timeout=self.timeout)
            soup = BeautifulSoup(r.text, "html.parser")
            iframe = soup.select_one("iframe#thatframe")
            if not iframe:
                return None

            iframe_url = iframe.get("src")
            if not iframe_url.startswith("http"):
                iframe_url = self.base_url + iframe_url

            r_iframe = self.session.get(iframe_url, timeout=self.timeout)
            m3u8_match = re.search(r"(https?://[^\s\"']+\.m3u8[^\s\"']*)", r_iframe.text)
            if not m3u8_match:
                return None

            m3u8_url = m3u8_match.group(1)

            # patch headers for playback
            parsed = urlparse(iframe_url)
            origin = f"{parsed.scheme}://{parsed.netloc}"
            headers = {
                "User-Agent": self.session.headers["User-Agent"],
                "Origin": origin,
                "Referer": iframe_url if iframe_url.endswith("/") else iframe_url + "/"
            }

            return {"url": m3u8_url, "headers": headers}
        except Exception as e:
            return None

    def get_items(self):
        items = []
        unique_hrefs = set()

        # fetch schedule JSON
        r = self.session.get(f"{self.base_url}/schedule/schedule-generated.json", timeout=self.timeout).json()
        for header, events in r.items():
            for event_type, event_list in events.items():
                for event in event_list:
                    title = event.get("event", "")
                    starttime = event.get("time", "")
                    league = event_type
                    channels = event.get("channels", [])
                    if isinstance(channels, dict):
                        channels = channels.values()

                    try:
                        utc_time = self.parse_header(header, starttime) - timedelta(hours=1)
                    except Exception:
                        try:
                            utc_time = datetime.now().replace(
                                hour=int(starttime.split(":")[0]),
                                minute=int(starttime.split(":")[1])
                            ) - timedelta(hours=1)
                        except:
                            utc_time = datetime.now()

                    links = []
                    for channel in channels:
                        page_url = f"{self.base_url}/stream/stream-{channel['channel_id']}.php"
                        resolved = self.resolve_m3u8(page_url)
                        if resolved:
                            links.append({
                                "name": channel["channel_name"],
                                "url": resolved["url"],
                                "headers": resolved["headers"]
                            })

                    items.append({
                        "title": title,
                        "league": league,
                        "starttime": utc_time.isoformat(),
                        "links": links
                    })

        # fetch 24/7 channels
        r_channels = self.session.get(f"{self.base_url}/24-7-channels.php", timeout=self.timeout)
        soup = BeautifulSoup(r_channels.text, "html.parser")
        A_link = soup.find_all('a')[:2]
        b_link = soup.find_all('a')[8:]
        links = A_link + b_link
        for link in links:
            title = link.text
            if '18+' in title:
                continue
            href = f"{self.base_url}{link['href']}"
            if href in unique_hrefs:
                continue
            unique_hrefs.add(href)

            resolved = self.resolve_m3u8(href)
            if resolved:
                items.append({
                    "title": title,
                    "league": "24/7",
                    "starttime": None,
                    "links": [{
                        "name": "Main",
                        "url": resolved["url"],
                        "headers": resolved["headers"]
                    }]
                })

        return items


if __name__ == "__main__":
    extractor = DaddyliveExtractor()
    data = extractor.get_items()
    with open("events.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
