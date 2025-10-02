import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from dateutil import parser
from datetime import datetime, timedelta
import json
import re

class DaddyliveExtractor:
    def __init__(self):
        self.domain = "dlhd.dad"
        self.base_url = f"https://{self.domain}"
        self.timeout = 15
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            )
        })

    def parse_header(self, header, time_str):
        """
        header is something like “Wednesday 02 October - …”
        time_str like “20:30”
        Force year = 2024 because site gives wrong year sometimes.
        """
        # Stop at the dash
        if "-" in header:
            date_part = header[:header.index("-")].strip()
        else:
            date_part = header.strip()
        dt = parser.parse(f"{date_part} {time_str}")
        dt = dt.replace(year=2024)
        return dt

    def resolve_m3u8(self, page_url):
        """Fetch the page, find iframe, parse embedded .m3u8, return url + headers."""
        try:
            resp = self.session.get(page_url, timeout=self.timeout)
            html = resp.text
        except Exception as e:
            print("Error fetching page:", page_url, e)
            return None

        soup = BeautifulSoup(html, "html.parser")
        iframe = soup.select_one("iframe#thatframe")
        if not iframe:
            # maybe there’s no iframe id=thatframe, try generic iframe
            iframe = soup.find("iframe")
        if not iframe:
            return None

        iframe_src = iframe.get("src")
        if not iframe_src:
            return None

        # make full URL if relative
        iframe_url = iframe_src if iframe_src.startswith("http") else urljoin(self.base_url, iframe_src)

        try:
            resp2 = self.session.get(iframe_url, timeout=self.timeout)
        except Exception as e:
            print("Error fetching iframe URL:", iframe_url, e)
            return None

        # try to find .m3u8 link in the iframe response
        # search for “.m3u8” in text
        m = re.search(r"(https?://[^\s\"']+\.m3u8[^\s\"']*)", resp2.text)
        if not m:
            return None
        m3u8_url = m.group(1)

        # compute Origin & Referer headers
        parsed = urlparse(iframe_url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        # ensure referer ends with slash
        referer = iframe_url
        if not referer.endswith("/"):
            referer = referer + "/"

        headers = {
            "User-Agent": self.session.headers.get("User-Agent"),
            "Origin": origin,
            "Referer": referer,
        }

        return {"url": m3u8_url, "headers": headers}

    def get_items(self):
        items = []
        unique_hrefs = set()

        # 1. schedule JSON
        try:
            resp = self.session.get(f"{self.base_url}/schedule/schedule-generated.json", timeout=self.timeout)
            rjson = resp.json()
        except Exception as e:
            print("Error fetching schedule JSON:", e)
            rjson = {}

        for header, events in rjson.items():
            for event_type, event_list in events.items():
                for event in event_list:
                    title = event.get("event", "")
                    time_str = event.get("time", "")
                    league = event_type
                    channels = event.get("channels", [])
                    if isinstance(channels, dict):
                        channels = channels.values()

                    try:
                        dt = self.parse_header(header, time_str) - timedelta(hours=1)
                    except Exception:
                        # fallback
                        try:
                            hh, mm = time_str.split(":")
                            dt = datetime.now().replace(hour=int(hh), minute=int(mm)) - timedelta(hours=1)
                        except:
                            dt = datetime.now()

                    link_entries = []
                    for ch in channels:
                        c_id = ch.get("channel_id")
                        c_name = ch.get("channel_name")
                        if c_id is None:
                            continue
                        page_url = f"{self.base_url}/stream/stream-{c_id}.php"
                        resolved = self.resolve_m3u8(page_url)
                        if resolved:
                            link_entries.append({
                                "name": c_name,
                                "url": resolved["url"],
                                "headers": resolved["headers"]
                            })

                    items.append({
                        "title": title,
                        "league": league,
                        "starttime": dt.isoformat(),
                        "links": link_entries
                    })

        # 2. 24/7 channels
        try:
            resp_ch = self.session.get(f"{self.base_url}/24-7-channels.php", timeout=self.timeout)
            soup = BeautifulSoup(resp_ch.text, "html.parser")
        except Exception as e:
            print("Error fetching 24-7 channels page:", e)
            soup = BeautifulSoup("", "html.parser")

        # the original script used first 2 <a> and then from index 8 onward
        a_all = soup.find_all("a")
        A_link = a_all[:2]
        B_link = a_all[8:]
        links = A_link + B_link
        for a in links:
            title = a.get_text().strip()
            if "18+" in title:
                continue
            href = a.get("href")
            if not href:
                continue
            full_href = href if href.startswith("http") else urljoin(self.base_url, href)
            if full_href in unique_hrefs:
                continue
            unique_hrefs.add(full_href)

            resolved = self.resolve_m3u8(full_href)
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
