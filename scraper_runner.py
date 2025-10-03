import json
import sys
import os
import requests
import re
import time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import undetected_chromedriver as uc

class StreamScraper:
    def __init__(self):
        self.driver = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    
    def init_driver(self):
        """Initialize undetected Chrome driver"""
        if self.driver is None:
            options = uc.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument(f'user-agent={self.headers["User-Agent"]}')
            
            self.driver = uc.Chrome(options=options)
            print("Chrome driver initialized")
    
    def close_driver(self):
        """Close the driver"""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def extract_m3u8_from_network(self, url, timeout=15):
        """
        Extract m3u8 URL by monitoring network requests
        """
        try:
            self.init_driver()
            
            # Enable network logging
            self.driver.execute_cdp_cmd('Network.enable', {})
            
            # Store network requests
            m3u8_urls = []
            
            def process_request(request):
                url = request.get('request', {}).get('url', '')
                if '.m3u8' in url:
                    m3u8_urls.append(url)
            
            # Navigate to page
            print(f"  Loading page: {url}")
            self.driver.get(url)
            
            # Wait for page to load
            time.sleep(3)
            
            # Get all network logs
            logs = self.driver.get_log('performance')
            
            for entry in logs:
                try:
                    log = json.loads(entry['message'])['message']
                    if log.get('method') == 'Network.requestWillBeSent':
                        request_url = log.get('params', {}).get('request', {}).get('url', '')
                        if '.m3u8' in request_url:
                            m3u8_urls.append(request_url)
                except:
                    pass
            
            # Also check page source for m3u8 URLs
            page_source = self.driver.page_source
            
            patterns = [
                r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']',
                r'source:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                r'file:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                r'src:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                r'(https?://[^\s<>"\']+\.m3u8[^\s<>"\']*)',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, page_source)
                m3u8_urls.extend(matches)
            
            # Remove duplicates and filter
            m3u8_urls = list(set(m3u8_urls))
            
            if m3u8_urls:
                # Prefer master.m3u8 or playlist.m3u8
                for url in m3u8_urls:
                    if 'master' in url.lower() or 'playlist' in url.lower():
                        return url
                return m3u8_urls[0]
            
            return None
            
        except Exception as e:
            print(f"  Error in extract_m3u8_from_network: {e}")
            return None
    
    def get_link(self, stream_page_url):
        """
        Extract the actual m3u8 stream URL from a stream page
        """
        try:
            print(f"  Extracting stream from: {stream_page_url}")
            
            # Get the stream page with requests first
            r = requests.get(stream_page_url, timeout=15, headers=self.headers)
            soup = BeautifulSoup(r.text, "html.parser")
            
            # Find the iframe containing the player
            iframe = soup.find("iframe")
            if not iframe:
                print("  No iframe found")
                return None
            
            iframe_src = iframe.get("src")
            if not iframe_src:
                print("  Iframe has no src")
                return None
            
            iframe_url = urljoin(stream_page_url, iframe_src)
            print(f"  Found iframe: {iframe_url}")
            
            # Use Selenium to extract m3u8 from iframe
            m3u8_url = self.extract_m3u8_from_network(iframe_url)
            
            if not m3u8_url:
                print("  No m3u8 URL found")
                return None
            
            print(f"  Found m3u8: {m3u8_url}")
            
            # Extract domain info for headers
            parsed = urlparse(m3u8_url)
            origin = f"{parsed.scheme}://{parsed.netloc}"
            
            return {
                'url': m3u8_url,
                'headers': {
                    'Origin': origin,
                    'Referer': iframe_url,
                    'User-Agent': self.headers['User-Agent']
                }
            }
            
        except Exception as e:
            print(f"  Error extracting stream: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def extract_full_title(self, game_element):
        """
        Extract full match title with both teams
        """
        try:
            # Try multiple methods to get full title
            
            # Method 1: Look for all text-success spans
            success_spans = game_element.select("span.text-success")
            if len(success_spans) >= 2:
                team1 = success_spans[0].text.strip()
                team2 = success_spans[1].text.strip()
                return f"{team1} vs {team2}"
            
            # Method 2: Get all text and parse
            full_text = game_element.get_text(separator='|', strip=True)
            
            # Remove time information
            full_text = re.sub(r'\d{2}:\d{2}\s*(AM|PM)?', '', full_text)
            
            # Try to find "vs" pattern
            vs_match = re.search(r'([^|]+?)\s+vs\s+([^|]+)', full_text, re.IGNORECASE)
            if vs_match:
                return f"{vs_match.group(1).strip()} vs {vs_match.group(2).strip()}"
            
            # Method 3: Look for multiple team images/names
            text_parts = [part.strip() for part in full_text.split('|') if part.strip()]
            # Filter out non-team text
            text_parts = [p for p in text_parts if len(p) > 2 and not re.match(r'^\d+:\d+', p)]
            
            if len(text_parts) >= 2:
                return f"{text_parts[0]} vs {text_parts[1]}"
            
            # Fallback: Use first text-success span
            title_tag = game_element.select_one("span.text-success")
            if title_tag:
                return title_tag.text.strip()
            
            return "Unknown Match"
            
        except Exception as e:
            print(f"  Error extracting title: {e}")
            return "Unknown Match"
    
    def get_games(self):
        """Scrape games from 720pstream"""
        games = []
        
        possible_domains = ["720pstream.lc", "720pstream.nu", "720pstream.me", "720pstream.ic"]
        base_url = None
        
        for domain in possible_domains:
            try:
                test_url = f"https://{domain}"
                print(f"Trying domain: {domain}")
                
                r = requests.get(test_url, timeout=10, headers=self.headers, verify=True)
                if r.status_code == 200:
                    base_url = test_url
                    print(f"Successfully connected to: {domain}")
                    break
            except Exception as e:
                print(f"Error connecting to {domain}: {str(e)}")
                continue
        
        if not base_url:
            print("Could not connect to any 720pstream domain")
            return []
        
        try:
            r = requests.get(base_url, timeout=15, headers=self.headers).text
            soup = BeautifulSoup(r, "html.parser")
            
            for li in soup.select("li.nav-item"):
                league = li.text.strip()
                
                a_tag = li.find("a")
                if not a_tag:
                    continue
                    
                href = a_tag.get("href")
                full_href = urljoin(base_url, href)
                
                print(f"\n{'='*60}")
                print(f"Processing league: {league}")
                print(f"{'='*60}")
                
                try:
                    r_league = requests.get(full_href, timeout=15, headers=self.headers).text
                    soup_league = BeautifulSoup(r_league, "html.parser")
                    
                    for game in soup_league.select("a.btn"):
                        # Extract full match title
                        game_title = self.extract_full_title(game)
                        
                        img_tag = game.select_one("img")
                        game_icon = urljoin(base_url, img_tag.get("src")) if img_tag else None
                        
                        game_href_raw = game.get("href")
                        game_href = urljoin(base_url, game_href_raw)
                        
                        # Extract time
                        game_time_tag = game.select_one("div.text-warning")
                        utc_time = None
                        
                        if game_time_tag and "24/7" not in game_time_tag.text:
                            time_tag = game_time_tag.find("time")
                            if time_tag:
                                time_str = time_tag.get("datetime")
                                try:
                                    if "-04" in time_str:
                                        utc_time = datetime(*(time.strptime(time_str, "%Y-%m-%dT%H:%M:%S-04:00")[:6])) + timedelta(hours=4)
                                    else:
                                        utc_time = datetime(*(time.strptime(time_str, "%Y-%m-%dT%H:%M:%S-05:00")[:6])) + timedelta(hours=5)
                                except:
                                    pass
                        
                        game_data = {
                            'title': game_title,
                            'league': league,
                            'icon': game_icon,
                            'starttime': utc_time.isoformat() if utc_time else None,
                            'link': game_href,
                            'stream_info': None
                        }
                        
                        # Extract stream URL
                        stream_info = self.get_link(game_href)
                        if stream_info:
                            game_data['stream_info'] = stream_info
                        
                        games.append(game_data)
                        print(f"  ✓ Added: {game_title}")
                        
                        # Small delay between requests
                        time.sleep(1)
                    
                    print(f"\nTotal games so far: {len(games)}")
                        
                except Exception as e:
                    print(f"Error fetching league {league}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            return games
                    
        except Exception as e:
            print(f"Error fetching main page: {e}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            self.close_driver()

def main():
    scraper = None
    try:
        print("="*60)
        print("Starting Advanced 720pStream Scraper")
        print(f"Current time: {datetime.utcnow().isoformat()}")
        print("="*60)
        
        scraper = StreamScraper()
        games = scraper.get_games()
        
        print(f"\n{'='*60}")
        print(f"SCRAPING COMPLETE - Found {len(games)} total games")
        print(f"{'='*60}")
        
        # Prepare output data
        output = {
            'timestamp': datetime.utcnow().isoformat(),
            'total_games': len(games),
            'games': games
        }
        
        # Write to JSON file
        with open('scraped_data.json', 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print("\n✓ Data successfully written to scraped_data.json")
        
        # Print summary
        if games:
            leagues = {}
            streams_found = 0
            for game in games:
                leagues[game['league']] = leagues.get(game['league'], 0) + 1
                if game.get('stream_info'):
                    streams_found += 1
            
            print(f"\n{'='*60}")
            print("SUMMARY")
            print(f"{'='*60}")
            for league, count in leagues.items():
                print(f"  {league}: {count} games")
            print(f"\nStreams extracted: {streams_found}/{len(games)} ({streams_found*100//len(games) if games else 0}%)")
        
    except Exception as e:
        print(f"\n❌ Error during scraping: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if scraper:
            scraper.close_driver()

if __name__ == "__main__":
    main()
