import json
import sys
import os
import requests
import re
import time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, unquote
import base64

class StreamScraper:
    def __init__(self):
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
    
    def extract_m3u8_advanced(self, url):
        """
        Advanced m3u8 extraction using multiple techniques
        """
        m3u8_urls = []
        
        try:
            print(f"  Loading iframe: {url}")
            
            # Method 1: Direct request and parse
            response = self.session.get(url, headers=self.headers, timeout=15)
            html_content = response.text
            
            # Method 2: Look for common JavaScript patterns
            js_patterns = [
                # Common player configurations
                r'source[s]?\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                r'file\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                r'src\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                r'hls\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                r'stream\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                r'video\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                
                # Direct URL patterns
                r'["\']?(https?://[^"\s\'<>]+\.m3u8[^"\s\'<>]*)["\']?',
                
                # Encoded patterns
                r'atob\(["\']([^"\']+)["\']\)',
                
                # JSON-like structures
                r'"url"\s*:\s*"([^"]+\.m3u8[^"]*)"',
                r'"hlsUrl"\s*:\s*"([^"]+\.m3u8[^"]*)"',
                r'"streamUrl"\s*:\s*"([^"]+\.m3u8[^"]*)"',
            ]
            
            for pattern in js_patterns:
                matches = re.findall(pattern, html_content, re.IGNORECASE)
                for match in matches:
                    # Check if it's base64 encoded
                    if 'atob' in pattern:
                        try:
                            decoded = base64.b64decode(match).decode('utf-8')
                            if '.m3u8' in decoded:
                                m3u8_urls.append(decoded)
                        except:
                            pass
                    else:
                        m3u8_urls.append(match)
            
            # Method 3: Look for embedded script tags
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Check all script tags
            for script in soup.find_all('script'):
                script_content = script.string
                if script_content:
                    # Look for m3u8 URLs in script content
                    script_m3u8 = re.findall(r'https?://[^\s<>"\']+\.m3u8[^\s<>"\']*', script_content)
                    m3u8_urls.extend(script_m3u8)
                    
                    # Look for base64 encoded content
                    b64_matches = re.findall(r'atob\(["\']([^"\']+)["\']\)', script_content)
                    for b64 in b64_matches:
                        try:
                            decoded = base64.b64decode(b64).decode('utf-8')
                            if '.m3u8' in decoded:
                                m3u8_urls.append(decoded)
                        except:
                            pass
            
            # Method 4: Check for data attributes
            for element in soup.find_all(attrs={'data-src': True}):
                data_src = element.get('data-src', '')
                if '.m3u8' in data_src:
                    m3u8_urls.append(data_src)
            
            # Method 5: Look for video/source tags
            for video in soup.find_all(['video', 'source']):
                src = video.get('src', '')
                if '.m3u8' in src:
                    m3u8_urls.append(src)
            
            # Method 6: Check for iframes within iframes
            nested_iframes = soup.find_all('iframe')
            for nested_iframe in nested_iframes:
                nested_src = nested_iframe.get('src', '')
                if nested_src and not nested_src.startswith('about:'):
                    nested_url = urljoin(url, nested_src)
                    print(f"  Found nested iframe: {nested_url}")
                    # Recursively check nested iframe
                    nested_m3u8 = self.extract_m3u8_advanced(nested_url)
                    if nested_m3u8:
                        return nested_m3u8
            
            # Method 7: Look for common embed patterns
            embed_patterns = [
                r'player\.load\(["\']([^"\']+)["\']',
                r'loadSource\(["\']([^"\']+)["\']',
                r'setupVideo\(["\']([^"\']+)["\']',
            ]
            
            for pattern in embed_patterns:
                matches = re.findall(pattern, html_content)
                for match in matches:
                    if '.m3u8' in match:
                        m3u8_urls.append(match)
            
            # Clean and validate URLs
            valid_m3u8_urls = []
            for m3u8_url in m3u8_urls:
                m3u8_url = m3u8_url.strip().strip('"\'')
                
                # Skip invalid URLs
                if not m3u8_url or len(m3u8_url) < 10:
                    continue
                
                # Make absolute URL
                if not m3u8_url.startswith('http'):
                    m3u8_url = urljoin(url, m3u8_url)
                
                # Validate URL format
                if m3u8_url.startswith('http') and '.m3u8' in m3u8_url:
                    valid_m3u8_urls.append(m3u8_url)
            
            # Remove duplicates
            valid_m3u8_urls = list(set(valid_m3u8_urls))
            
            if valid_m3u8_urls:
                # Prefer master.m3u8 or playlist.m3u8
                for url in valid_m3u8_urls:
                    if 'master' in url.lower() or 'playlist' in url.lower():
                        print(f"  ✓ Found m3u8: {url}")
                        return url
                
                # Otherwise return first valid URL
                print(f"  ✓ Found m3u8: {valid_m3u8_urls[0]}")
                return valid_m3u8_urls[0]
            
            print(f"  ✗ No m3u8 found")
            return None
            
        except Exception as e:
            print(f"  Error extracting m3u8: {e}")
            return None
    
    def get_link(self, stream_page_url):
        """
        Extract the actual m3u8 stream URL from a stream page
        """
        try:
            print(f"  Extracting stream from: {stream_page_url}")
            
            # Get the stream page
            r = self.session.get(stream_page_url, headers=self.headers, timeout=15)
            soup = BeautifulSoup(r.text, "html.parser")
            
            # Find the iframe containing the player
            iframe = soup.find("iframe")
            if not iframe:
                print("  ✗ No iframe found")
                return None
            
            iframe_src = iframe.get("src")
            if not iframe_src:
                print("  ✗ Iframe has no src")
                return None
            
            iframe_url = urljoin(stream_page_url, iframe_src)
            print(f"  → Iframe: {iframe_url}")
            
            # Extract m3u8 from iframe
            m3u8_url = self.extract_m3u8_advanced(iframe_url)
            
            if not m3u8_url:
                return None
            
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
            print(f"  ✗ Error extracting stream: {e}")
            return None
    
    def extract_full_title(self, game_element):
        """
        Extract full match title with both teams
        """
        try:
            # Method 1: Look for all text-success spans (usually contains team names)
            success_spans = game_element.select("span.text-success")
            if len(success_spans) >= 2:
                team1 = success_spans[0].text.strip()
                team2 = success_spans[1].text.strip()
                return f"{team1} vs {team2}"
            
            # Method 2: Parse from full text
            full_text = game_element.get_text(separator=' | ', strip=True)
            
            # Remove time information
            full_text = re.sub(r'\d{2}:\d{2}\s*(AM|PM)?', '', full_text)
            full_text = re.sub(r'\b(LIVE|24/7|HD)\b', '', full_text, flags=re.IGNORECASE)
            
            # Try to find "vs" pattern
            vs_match = re.search(r'([^|]+?)\s+vs\.?\s+([^|]+)', full_text, re.IGNORECASE)
            if vs_match:
                team1 = vs_match.group(1).strip()
                team2 = vs_match.group(2).strip()
                return f"{team1} vs {team2}"
            
            # Method 3: Split by separator and find team names
            parts = [p.strip() for p in full_text.split('|')]
            parts = [p for p in parts if len(p) > 2 and not re.match(r'^\d+:\d+', p)]
            
            if len(parts) >= 2:
                return f"{parts[0]} vs {parts[1]}"
            
            # Method 4: Check for h5 or strong tags
            title_tag = game_element.find(['h5', 'strong', 'span'])
            if title_tag:
                title = title_tag.get_text(strip=True)
                # Clean up
                title = re.sub(r'\d{2}:\d{2}\s*(AM|PM)?', '', title)
                if title:
                    return title
            
            # Fallback: Use first text-success span
            if success_spans:
                return success_spans[0].text.strip()
            
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
                print(f"Testing domain: {domain}")
                
                r = self.session.get(test_url, timeout=10, headers=self.headers, verify=True)
                if r.status_code == 200:
                    base_url = test_url
                    print(f"✓ Connected to: {domain}\n")
                    break
            except Exception as e:
                print(f"✗ Failed: {str(e)}")
                continue
        
        if not base_url:
            print("Could not connect to any 720pstream domain")
            return []
        
        try:
            r = self.session.get(base_url, timeout=15, headers=self.headers).text
            soup = BeautifulSoup(r, "html.parser")
            
            for li in soup.select("li.nav-item"):
                league = li.text.strip()
                
                a_tag = li.find("a")
                if not a_tag:
                    continue
                    
                href = a_tag.get("href")
                full_href = urljoin(base_url, href)
                
                print(f"\n{'='*70}")
                print(f"📺 {league}")
                print(f"{'='*70}")
                
                try:
                    r_league = self.session.get(full_href, timeout=15, headers=self.headers).text
                    soup_league = BeautifulSoup(r_league, "html.parser")
                    
                    game_buttons = soup_league.select("a.btn")
                    print(f"Found {len(game_buttons)} games in {league}\n")
                    
                    for idx, game in enumerate(game_buttons, 1):
                        print(f"[{idx}/{len(game_buttons)}] Processing...")
                        
                        # Extract full match title
                        game_title = self.extract_full_title(game)
                        
                        img_tag = game.select_one("img")
                        game_icon = urljoin(base_url, img_tag.get("src")) if img_tag and img_tag.get("src") else None
                        
                        game_href_raw = game.get("href")
                        game_href = urljoin(base_url, game_href_raw)
                        
                        # Extract time
                        game_time_tag = game.select_one("div.text-warning, span.text-warning")
                        utc_time = None
                        
                        if game_time_tag and "24/7" not in game_time_tag.text:
                            time_tag = game_time_tag.find("time")
                            if time_tag and time_tag.get("datetime"):
                                time_str = time_tag.get("datetime")
                                try:
                                    # Parse different timezone formats
                                    if "-04:00" in time_str:
                                        utc_time = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%S-04:00") + timedelta(hours=4)
                                    elif "-05:00" in time_str:
                                        utc_time = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%S-05:00") + timedelta(hours=5)
                                    else:
                                        # Try generic parsing
                                        utc_time = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                                except Exception as e:
                                    print(f"  Warning: Could not parse time: {e}")
                        
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
                        print(f"  ✓ {game_title}\n")
                        
                        # Delay to avoid rate limiting
                        time.sleep(0.5)
                    
                    print(f"{'='*70}")
                    print(f"Completed {league}: {len(game_buttons)} games")
                    print(f"Total games collected: {len(games)}")
                    print(f"{'='*70}\n")
                        
                except Exception as e:
                    print(f"✗ Error fetching league {league}: {e}\n")
                    import traceback
                    traceback.print_exc()
                    continue
            
            return games
                    
        except Exception as e:
            print(f"✗ Error fetching main page: {e}")
            import traceback
            traceback.print_exc()
            return []

def main():
    scraper = None
    try:
        print("="*70)
        print("🚀 720pStream Advanced Scraper")
        print(f"⏰ Started at: {datetime.utcnow().isoformat()} UTC")
        print("="*70 + "\n")
        
        scraper = StreamScraper()
        games = scraper.get_games()
        
        print(f"\n{'='*70}")
        print(f"✅ SCRAPING COMPLETE")
        print(f"{'='*70}")
        print(f"📊 Total games found: {len(games)}")
        
        # Prepare output data
        output = {
            'timestamp': datetime.utcnow().isoformat(),
            'total_games': len(games),
            'games': games
        }
        
        # Write to JSON file
        with open('scraped_data.json', 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Data saved to: scraped_data.json")
        
        # Print summary
        if games:
            leagues = {}
            streams_found = 0
            for game in games:
                leagues[game['league']] = leagues.get(game['league'], 0) + 1
                if game.get('stream_info'):
                    streams_found += 1
            
            print(f"\n{'='*70}")
            print("📈 STATISTICS")
            print(f"{'='*70}")
            for league, count in sorted(leagues.items()):
                print(f"  {league:<20} {count:>3} games")
            print(f"{'='*70}")
            print(f"  🎬 Streams extracted: {streams_found}/{len(games)} ({streams_found*100//len(games) if games else 0}%)")
            print(f"{'='*70}")
        
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
