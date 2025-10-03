import requests
from bs4 import BeautifulSoup
from dateutil import parser
from datetime import datetime, timedelta
import json
import re
from urllib.parse import urlparse, urljoin
import time
import random

# Disable SSL warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class DaddyliveScraper:
    def __init__(self):
        self.domains = ["dlhd.dad"]
        self.session = requests.Session()
        self.session.verify = False
        
        # More realistic headers
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'iframe',  # Changed to 'iframe'
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'cross-site',  # Changed to 'cross-site'
            'Cache-Control': 'max-age=0',
        }
        
    def random_delay(self, min_sec=1, max_sec=3):
        """Add random delay to avoid rate limiting"""
        time.sleep(random.uniform(min_sec, max_sec))
    
    def extract_m3u8_from_page(self, url, parent_url):
        """Extract m3u8 link from page with proper iframe headers"""
        try:
            headers = self.headers.copy()
            # CRITICAL: Set referer to the parent stream page, not the embed URL itself
            headers['Referer'] = parent_url
            headers['Sec-Fetch-Dest'] = 'iframe'
            headers['Sec-Fetch-Mode'] = 'navigate'
            headers['Sec-Fetch-Site'] = 'cross-site'
            
            # First request might be blocked, but establishes session
            response = self.session.get(url, headers=headers, timeout=20, allow_redirects=True)
            
            # Check if we got blocked
            if 'direct access blocked' in response.text.lower() or response.status_code == 403:
                print(f"    ⚠ Blocked by referer check, trying alternative methods...")
                return None
            
            text = response.text
            
            # Extended patterns for m3u8 detection
            m3u8_patterns = [
                # Jwplayer and common video players
                r'source\s*:\s*["\']([^"\']*\.m3u8[^"\']*)["\']',
                r'file\s*:\s*["\']([^"\']*\.m3u8[^"\']*)["\']',
                r'src\s*:\s*["\']([^"\']*\.m3u8[^"\']*)["\']',
                # Variable assignments
                r'var\s+\w+\s*=\s*["\']([^"\']*\.m3u8[^"\']*)["\']',
                r'const\s+\w+\s*=\s*["\']([^"\']*\.m3u8[^"\']*)["\']',
                r'let\s+\w+\s*=\s*["\']([^"\']*\.m3u8[^"\']*)["\']',
                # Direct URLs with various quote styles
                r'["\']([^"\']*//[^"\']*\.m3u8[^"\']*)["\']',
                r'(https?://[^\s<>"\'()]+\.m3u8(?:\?[^\s<>"\'()]*)?)',
                # In data attributes
                r'data-[\w-]+\s*=\s*["\']([^"\']*\.m3u8[^"\']*)["\']',
                # URL encoded
                r'url\s*=\s*([^\s&]+\.m3u8[^\s&]*)',
            ]
            
            found_urls = []
            for pattern in m3u8_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                found_urls.extend(matches)
            
            # Check for base64 encoded URLs
            base64_pattern = r'atob\(["\']([A-Za-z0-9+/=]{20,})["\']'
            base64_matches = re.findall(base64_pattern, text)
            for b64 in base64_matches:
                try:
                    import base64
                    decoded = base64.b64decode(b64).decode('utf-8', errors='ignore')
                    if '.m3u8' in decoded:
                        found_urls.append(decoded)
                except:
                    pass
            
            # Process and validate found URLs
            for m3u8_url in found_urls:
                # Clean up the URL
                m3u8_url = m3u8_url.split('"')[0].split("'")[0].split('\\')[0].strip()
                m3u8_url = m3u8_url.replace('\\/', '/')
                
                # Skip invalid URLs
                if not m3u8_url or len(m3u8_url) < 10:
                    continue
                
                # Skip obvious non-URLs
                if m3u8_url.startswith('javascript:') or m3u8_url.startswith('data:'):
                    continue
                
                # Make absolute URL
                if m3u8_url.startswith('//'):
                    m3u8_url = 'https:' + m3u8_url
                elif m3u8_url.startswith('/'):
                    parsed = urlparse(url)
                    m3u8_url = f"{parsed.scheme}://{parsed.netloc}{m3u8_url}"
                elif not m3u8_url.startswith('http'):
                    # Try to resolve relative URL
                    try:
                        m3u8_url = urljoin(url, m3u8_url)
                    except:
                        continue
                
                # Return first valid-looking m3u8 URL
                # We skip validation to avoid additional blocked requests
                parsed_url = urlparse(url)
                return {
                    'url': m3u8_url,
                    'headers': {
                        'Origin': f"https://{parsed_url.netloc}",
                        'Referer': url,
                        'User-Agent': self.headers['User-Agent']
                    }
                }
            
            return None
            
        except Exception as e:
            print(f"    ✗ Exception: {str(e)[:80]}")
            return None
    
    def get_stream_link(self, stream_url):
        """Get the playable m3u8 link from a stream page"""
        try:
            headers = self.headers.copy()
            # First visit to get cookies and establish session
            headers['Sec-Fetch-Dest'] = 'document'
            headers['Sec-Fetch-Site'] = 'none'
            
            response = self.session.get(stream_url, headers=headers, timeout=20)
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Method 1: Look for iframe with ID
            iframe = soup.select_one("iframe#thatframe")
            
            # Method 2: Look for any iframe
            if not iframe:
                iframes = soup.find_all("iframe")
                # Filter out ads/tracking iframes
                for ifr in iframes:
                    src = ifr.get("src", "")
                    if src and not any(x in src.lower() for x in ['ad', 'doubleclick', 'analytics', 'pixel']):
                        iframe = ifr
                        break
            
            # Method 3: Look in JavaScript
            if not iframe:
                scripts = soup.find_all('script')
                for script in scripts:
                    if script.string:
                        # Look for iframe creation in JS
                        iframe_matches = re.findall(
                            r'(?:iframe\.src|src\s*=|setAttribute\(["\']src["\']\s*,)\s*["\']([^"\']+)["\']', 
                            script.string
                        )
                        for match in iframe_matches:
                            if not any(x in match.lower() for x in ['ad', 'doubleclick', 'analytics']):
                                class MockIframe:
                                    def __init__(self, src):
                                        self.src = src
                                    def get(self, attr):
                                        return self.src if attr == "src" else None
                                iframe = MockIframe(match)
                                break
                        if iframe:
                            break
            
            if iframe and iframe.get("src"):
                iframe_src = iframe.get("src")
                
                # Make absolute URL
                if iframe_src.startswith("//"):
                    iframe_src = "https:" + iframe_src
                elif iframe_src.startswith("/"):
                    parsed = urlparse(stream_url)
                    iframe_src = f"{parsed.scheme}://{parsed.netloc}{iframe_src}"
                elif not iframe_src.startswith("http"):
                    iframe_src = urljoin(stream_url, iframe_src)
                
                # Add slight delay
                self.random_delay(0.3, 0.8)
                
                # Extract m3u8, passing the parent URL as referer
                m3u8_data = self.extract_m3u8_from_page(iframe_src, stream_url)
                return m3u8_data
            
            return None
            
        except Exception as e:
            print(f"    ✗ Error: {str(e)[:80]}")
            return None
    
    def scrape_schedule(self):
        """Scrape scheduled events"""
        items = []
        try:
            url = f"https://{self.domains[0]}/schedule/schedule-generated.json"
            response = self.session.get(url, headers=self.headers, timeout=30)
            
            text = response.text.strip()
            
            # Clean JavaScript wrapper
            if 'var ' in text or 'const ' in text or 'let ' in text:
                match = re.search(r'[{[].*[}\]]', text, re.DOTALL)
                if match:
                    text = match.group(0)
            
            data = json.loads(text)
            
            for header, events in data.items():
                for event_type, event_list in events.items():
                    for event in event_list:
                        title = event.get("event", "")
                        starttime = event.get("time", "")
                        league = event_type
                        channels = event.get("channels", [])
                        
                        if isinstance(channels, dict):
                            channels = list(channels.values())
                        
                        try:
                            timestamp = parser.parse(header[:header.index("-")] + " " + starttime)
                            timestamp = timestamp.replace(year=datetime.now().year)
                            utc_time = timestamp - timedelta(hours=1)
                        except:
                            try:
                                utc_time = datetime.now().replace(
                                    hour=int(starttime.split(":")[0]), 
                                    minute=int(starttime.split(":")[1])
                                ) - timedelta(hours=1)
                            except:
                                utc_time = datetime.now()
                        
                        items.append({
                            "title": title,
                            "league": league,
                            "starttime": utc_time.isoformat(),
                            "links": [
                                {
                                    "address": f"https://{self.domains[0]}/stream/stream-{ch['channel_id']}.php",
                                    "name": ch["channel_name"],
                                    "m3u8": None
                                } for ch in channels
                            ]
                        })
            
            print(f"✓ Scraped {len(items)} scheduled events")
            
        except Exception as e:
            print(f"✗ Error scraping schedule: {e}")
        
        return items
    
    def scrape_247_channels(self):
        """Scrape 24/7 channels"""
        items = []
        
        try:
            url = f"https://{self.domains[0]}/daddy.json"
            response = self.session.get(url, headers=self.headers, timeout=30)
            channels_data = response.json()
            
            if isinstance(channels_data, list):
                for channel in channels_data:
                    if isinstance(channel, dict):
                        self._process_247_channel(channel, items)
            elif isinstance(channels_data, dict):
                for key, channel in channels_data.items():
                    if isinstance(channel, dict):
                        self._process_247_channel(channel, items)
            
            print(f"✓ Scraped {len(items)} 24/7 channels")
            
        except Exception as e:
            print(f"✗ daddy.json failed, trying fallback...")
            
            try:
                url = f"https://{self.domains[0]}/24-7-channels.php"
                response = self.session.get(url, headers=self.headers, timeout=30)
                soup = BeautifulSoup(response.text, "html.parser")
                
                links = soup.find_all('a')
                unique_hrefs = set()
                
                for link in links:
                    title = link.text.strip()
                    if '18+' in title or not title:
                        continue
                    
                    href = link.get('href')
                    if not href:
                        continue
                    
                    full_url = urljoin(f"https://{self.domains[0]}", href)
                    
                    if full_url in unique_hrefs:
                        continue
                    unique_hrefs.add(full_url)
                    
                    items.append({
                        "title": title,
                        "league": "24/7",
                        "starttime": None,
                        "links": [{
                            "address": full_url,
                            "name": title,
                            "m3u8": None
                        }]
                    })
                
                print(f"✓ Fallback: scraped {len(items)} channels")
                
            except Exception as fe:
                print(f"✗ Fallback also failed: {fe}")
        
        return items
    
    def _process_247_channel(self, channel, items):
        """Process a single 24/7 channel"""
        title = channel.get('name', channel.get('title', 'Unknown'))
        channel_id = channel.get('id', channel.get('channel_id', ''))
        
        if '18+' in title:
            return
        
        href = f"https://{self.domains[0]}/stream/stream-{channel_id}.php"
        
        items.append({
            "title": title,
            "league": "24/7",
            "starttime": None,
            "links": [{
                "address": href,
                "name": title,
                "m3u8": None
            }]
        })
    
    def run(self, resolve_m3u8=True, max_resolve=15):
        """Run the complete scraper"""
        print("=" * 60)
        print("Daddylive Scraper - Enhanced Version v2")
        print("=" * 60)
        
        schedule_items = self.scrape_schedule()
        channel_items = self.scrape_247_channels()
        all_items = schedule_items + channel_items
        
        print(f"\n✓ Total items: {len(all_items)}")
        
        if resolve_m3u8 and max_resolve > 0:
            print(f"\n{'=' * 60}")
            print(f"Resolving M3U8 (limit: {max_resolve})")
            print(f"Note: Many streams use iframe protection and may not resolve")
            print("=" * 60)
            
            resolved_count = 0
            items_to_resolve = [item for item in all_items if item.get('links')]
            
            for idx, item in enumerate(items_to_resolve[:max_resolve], 1):
                for link in item.get('links', []):
                    stream_url = link.get('address')
                    if stream_url and '/stream/' in stream_url:
                        title_short = item['title'][:50]
                        print(f"\n[{idx}/{min(max_resolve, len(items_to_resolve))}] {title_short}")
                        
                        m3u8_data = self.get_stream_link(stream_url)
                        
                        if m3u8_data:
                            link['m3u8'] = m3u8_data
                            resolved_count += 1
                            url_preview = m3u8_data['url'][:60] + "..." if len(m3u8_data['url']) > 60 else m3u8_data['url']
                            print(f"  ✓ Found: {url_preview}")
                        else:
                            print(f"  ✗ Not found")
                        
                        # Delay between requests
                        if idx < min(max_resolve, len(items_to_resolve)):
                            self.random_delay(2, 4)
            
            print(f"\n{'=' * 60}")
            print(f"✓ Resolved: {resolved_count}/{max_resolve}")
            if resolved_count == 0:
                print("⚠ No m3u8 links found - site may use advanced protection")
            print("=" * 60)
        
        output = {
            "scraped_at": datetime.utcnow().isoformat() + "Z",
            "total_items": len(all_items),
            "scheduled_events": len(schedule_items),
            "247_channels": len(channel_items),
            "resolved_m3u8_count": sum(
                1 for item in all_items 
                for link in item.get('links', []) 
                if link.get('m3u8')
            ),
            "items": all_items
        }
        
        with open('daddylive_data.json', 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Saved to daddylive_data.json")
        return output


if __name__ == "__main__":
    import sys
    
    # Get max_resolve from command line or use default
    max_resolve = 15
    if len(sys.argv) > 1:
        try:
            max_resolve = int(sys.argv[1])
        except:
            pass
    
    scraper = DaddyliveScraper()
    scraper.run(resolve_m3u8=True, max_resolve=max_resolve)
