import requests
from bs4 import BeautifulSoup
import json
import os
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse

class StreamBTWExtractor:
    def __init__(self):
        self.domains = ["streambtw.com"]
        self.name = "StreamBTW"
        self.timeout = 30
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        
        # Sport icons mapping
        self.icons = {
            "football": "🏈",
            "soccer": "⚽",
            "basketball": "🏀",
            "baseball": "⚾",
            "hockey": "🏒",
            "tennis": "🎾",
            "rugby": "🏉",
            "cricket": "🏏",
            "volleyball": "🏐",
            "golf": "⛳",
            "boxing": "🥊",
            "mma": "🥋",
            "motorsport": "🏎️",
            "racing": "🏁"
        }
    
    def find_iframes(self, url: str) -> List[Dict[str, str]]:
        """Find iframe sources in a webpage"""
        try:
            headers = {
                "User-Agent": self.user_agent,
                "Referer": f"https://{self.domains[0]}/"
            }
            r = requests.get(url, headers=headers, timeout=self.timeout)
            r.raise_for_status()
            
            soup = BeautifulSoup(r.text, "html.parser")
            iframes = []
            
            # Find all iframe tags
            for iframe in soup.find_all("iframe"):
                src = iframe.get("src") or iframe.get("data-src")
                if src:
                    # Handle relative URLs
                    if src.startswith("//"):
                        src = "https:" + src
                    elif src.startswith("/"):
                        src = f"https://{self.domains[0]}{src}"
                    iframes.append({"url": src, "type": "iframe_tag"})
            
            # Also check for iframes in script tags
            for script in soup.find_all("script"):
                if script.string:
                    # Look for iframe URLs in JavaScript
                    iframe_matches = re.findall(r'(?:iframe|src)[\s]*[=:][\s]*["\']([^"\']+)["\']', script.string)
                    for match in iframe_matches:
                        if match.startswith("http"):
                            iframes.append({"url": match, "type": "script_tag"})
            
            return iframes
        except Exception as e:
            print(f"    ⚠️ Error finding iframes: {e}")
            return []
    
    def scan_page_for_m3u8(self, url: str, referer: str = "") -> Optional[str]:
        """
        Scan a page for M3U8 stream URLs
        Checks: direct links, JavaScript variables, embedded data, API calls
        """
        try:
            headers = {
                "User-Agent": self.user_agent,
                "Referer": referer if referer else url
            }
            
            print(f"    🔍 Scanning page for M3U8: {url}")
            r = requests.get(url, headers=headers, timeout=self.timeout)
            r.raise_for_status()
            
            content = r.text
            
            # Method 1: Direct M3U8 links in HTML
            m3u8_patterns = [
                r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']',
                r'source:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                r'file:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                r'src:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                r'playlist:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            ]
            
            for pattern in m3u8_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    m3u8_url = matches[0]
                    # Handle relative URLs
                    if not m3u8_url.startswith('http'):
                        m3u8_url = urljoin(url, m3u8_url)
                    print(f"    ✅ Found M3U8 (direct): {m3u8_url}")
                    return m3u8_url
            
            # Method 2: Base64 encoded M3U8
            base64_pattern = r'atob\(["\']([A-Za-z0-9+/=]+)["\']\)'
            base64_matches = re.findall(base64_pattern, content)
            for b64 in base64_matches:
                try:
                    import base64
                    decoded = base64.b64decode(b64).decode('utf-8')
                    if '.m3u8' in decoded:
                        if not decoded.startswith('http'):
                            decoded = urljoin(url, decoded)
                        print(f"    ✅ Found M3U8 (base64): {decoded}")
                        return decoded
                except:
                    continue
            
            # Method 3: JSON responses with stream URLs
            json_patterns = [
                r'"url":\s*"([^"]+\.m3u8[^"]*)"',
                r'"stream":\s*"([^"]+\.m3u8[^"]*)"',
                r'"hls":\s*"([^"]+\.m3u8[^"]*)"',
                r'"source":\s*"([^"]+\.m3u8[^"]*)"',
            ]
            
            for pattern in json_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    m3u8_url = matches[0].replace('\\/', '/')
                    if not m3u8_url.startswith('http'):
                        m3u8_url = urljoin(url, m3u8_url)
                    print(f"    ✅ Found M3U8 (JSON): {m3u8_url}")
                    return m3u8_url
            
            # Method 4: Check for API endpoints that might return M3U8
            api_patterns = [
                r'["\'](https?://[^"\']+/api/[^"\']+stream[^"\']*)["\']',
                r'["\'](https?://[^"\']+/playlist[^"\']*)["\']',
                r'["\'](https?://[^"\']+/get[^"\']*stream[^"\']*)["\']',
            ]
            
            for pattern in api_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for api_url in matches:
                    try:
                        api_response = requests.get(api_url, headers=headers, timeout=10)
                        if '.m3u8' in api_response.text:
                            # Try to extract M3U8 from API response
                            api_m3u8 = re.findall(r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', api_response.text)
                            if api_m3u8:
                                print(f"    ✅ Found M3U8 (API): {api_m3u8[0]}")
                                return api_m3u8[0]
                    except:
                        continue
            
            print(f"    ❌ No M3U8 found on page")
            return None
            
        except Exception as e:
            print(f"    ❌ Error scanning page: {e}")
            return None
    
    def get_items(self) -> List[Dict[str, Any]]:
        """Extract all sports streaming items from StreamBTW"""
        items = []
        
        try:
            print(f"🔍 Fetching data from https://{self.domains[0]}...")
            
            headers = {
                "User-Agent": self.user_agent
            }
            r = requests.get(f"https://{self.domains[0]}", headers=headers, timeout=self.timeout)
            r.raise_for_status()
            
            soup = BeautifulSoup(r.text, "html.parser")
            
            # Extract items from card divs
            cards = soup.select("div.card")
            print(f"📦 Found {len(cards)} cards")
            
            for idx, card in enumerate(cards, 1):
                try:
                    # Extract game titles
                    game_titles = [title.text.strip() for title in card.select("p")]
                    
                    # Extract links
                    hrefs = [link.get("href") for link in card.select("a")]
                    
                    # Extract sport types
                    sports = [title.text.strip() for title in card.select("h5")]
                    
                    # Extract thumbnails
                    thumbs = [icon.get("src") for icon in card.select("img")]
                    
                    # Combine data
                    for title, sport, href, thumb in zip(game_titles, sports, hrefs, thumbs):
                        # Handle relative URLs
                        if href and not href.startswith("http"):
                            href = f"https://{self.domains[0]}{href}" if href.startswith("/") else f"https://{self.domains[0]}/{href}"
                        
                        if thumb and not thumb.startswith("http"):
                            thumb = f"https://{self.domains[0]}{thumb}" if thumb.startswith("/") else f"https://{self.domains[0]}/{thumb}"
                        
                        item = {
                            "title": title,
                            "sport": sport.upper() if sport else "UNKNOWN",
                            "icon": self.icons.get(sport.lower(), "🎯") if sport else "🎯",
                            "link": href,
                            "thumbnail": thumb,
                            "extracted_at": datetime.utcnow().isoformat()
                        }
                        items.append(item)
                        print(f"  ✅ [{idx}] {sport}: {title}")
                
                except Exception as e:
                    print(f"  ⚠️ Error processing card {idx}: {e}")
                    continue
            
            print(f"\n✅ Successfully extracted {len(items)} items")
            
        except requests.RequestException as e:
            print(f"❌ Request error: {e}")
        except Exception as e:
            print(f"❌ Extraction error: {e}")
        
        return items
    
    def get_link(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Get playable video link with proper headers
        1. Opens the page and finds iframes
        2. Scans iframe for M3U8 stream URL
        3. Patches headers with Referer/Origin/User-Agent
        """
        try:
            print(f"  🎬 Getting playable link from: {url}")
            
            # Step 1: Find iframes on the page
            iframes = self.find_iframes(url)
            
            if not iframes:
                print(f"    ⚠️ No iframes found, trying direct M3U8 scan")
                m3u8_url = self.scan_page_for_m3u8(url, url)
                if m3u8_url:
                    return self._create_playable_link(m3u8_url, url, url)
                return None
            
            print(f"    📺 Found {len(iframes)} iframe(s)")
            
            # Step 2: Scan each iframe for M3U8
            for idx, iframe_info in enumerate(iframes, 1):
                iframe_url = iframe_info["url"]
                print(f"    [{idx}/{len(iframes)}] Checking iframe: {iframe_url}")
                
                # Scan the iframe page for M3U8
                m3u8_url = self.scan_page_for_m3u8(iframe_url, url)
                
                if m3u8_url:
                    # Step 3: Create playable link with patched headers
                    return self._create_playable_link(m3u8_url, iframe_url, url)
            
            print(f"    ❌ No playable M3U8 found in any iframe")
            return None
            
        except Exception as e:
            print(f"    ❌ Error getting link: {e}")
            return None
    
    def _create_playable_link(self, m3u8_url: str, iframe_url: str, page_url: str) -> Dict[str, Any]:
        """
        Create a playable link with proper headers for Referer/Origin restrictions
        """
        # Parse URLs to get origins
        iframe_parsed = urlparse(iframe_url)
        page_parsed = urlparse(page_url)
        m3u8_parsed = urlparse(m3u8_url)
        
        # Determine the best origin and referer
        origin = f"{iframe_parsed.scheme}://{iframe_parsed.netloc}"
        referer = iframe_url
        
        # Build headers that bypass most restrictions
        headers = {
            "User-Agent": self.user_agent,
            "Referer": referer,
            "Origin": origin,
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "cross-site"
        }
        
        # Test if the M3U8 is accessible
        is_accessible = self._test_m3u8_access(m3u8_url, headers)
        
        playable_link = {
            "m3u8_url": m3u8_url,
            "iframe_url": iframe_url,
            "page_url": page_url,
            "headers": headers,
            "is_accessible": is_accessible,
            "origin": origin,
            "referer": referer,
            "extracted_at": datetime.utcnow().isoformat()
        }
        
        print(f"    ✅ Playable link created: {m3u8_url[:80]}...")
        print(f"    📋 Headers patched: Origin={origin}, Referer={referer[:50]}...")
        print(f"    🎯 Accessible: {is_accessible}")
        
        return playable_link
    
    def _test_m3u8_access(self, m3u8_url: str, headers: Dict[str, str]) -> bool:
        """Test if the M3U8 URL is accessible with the given headers"""
        try:
            response = requests.head(m3u8_url, headers=headers, timeout=10, allow_redirects=True)
            return response.status_code == 200
        except:
            # If HEAD fails, try GET with a short timeout
            try:
                response = requests.get(m3u8_url, headers=headers, timeout=10, stream=True)
                # Just read a tiny bit to confirm it's valid
                next(response.iter_content(1024), None)
                return response.status_code == 200
            except:
                return False

def main():
    print("="*60)
    print("🏆 StreamBTW Sports Streaming Extractor")
    print("="*60 + "\n")
    
    extractor = StreamBTWExtractor()
    
    # Extract all items
    items = extractor.get_items()
    
    # Check extraction mode
    extract_playable = os.getenv('EXTRACT_PLAYABLE', 'false').lower() == 'true'
    extract_iframes = os.getenv('EXTRACT_IFRAMES', 'false').lower() == 'true'
    
    # If playable extraction is enabled, extract M3U8 links
    if extract_playable and items:
        print(f"\n🔍 Extracting playable M3U8 links for {len(items)} items...")
        print(f"⚠️  This will take several minutes...\n")
        
        for idx, item in enumerate(items, 1):
            if item.get('link'):
                print(f"[{idx}/{len(items)}] {item['sport']} - {item['title']}")
                playable_link = extractor.get_link(item['link'])
                if playable_link:
                    item['playable_link'] = playable_link
                    print(f"  ✅ M3U8 extracted\n")
                else:
                    print(f"  ❌ Failed to extract M3U8\n")
    
    elif extract_iframes and items:
        print(f"\n🔍 Extracting iframe details for {len(items)} items...")
        
        for idx, item in enumerate(items, 1):
            if item.get('link'):
                print(f"[{idx}/{len(items)}] Processing: {item['title']}")
                iframes = extractor.find_iframes(item['link'])
                if iframes:
                    item['iframes'] = iframes
                    item['iframe_count'] = len(iframes)
                    print(f"  ✅ Found {len(iframes)} iframes\n")
    
    # Organize by sport
    sports_data = {}
    for item in items:
        sport = item['sport']
        if sport not in sports_data:
            sports_data[sport] = []
        sports_data[sport].append(item)
    
    # Count streams with M3U8
    m3u8_count = sum(1 for item in items if 'playable_link' in item and item['playable_link'].get('m3u8_url'))
    accessible_count = sum(1 for item in items if 'playable_link' in item and item['playable_link'].get('is_accessible'))
    
    # Prepare output
    output_data = {
        "extractor": "StreamBTW",
        "last_updated": datetime.utcnow().isoformat(),
        "total_items": len(items),
        "sports_count": len(sports_data),
        "m3u8_extracted": m3u8_count,
        "accessible_streams": accessible_count,
        "sports": list(sports_data.keys()),
        "items": items,
        "by_sport": sports_data
    }
    
    # Save to JSON
    output_file = 'streambtw_data.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    # Print summary
    print("\n" + "="*60)
    print("📊 Extraction Summary:")
    print("="*60)
    print(f"  📦 Total Items: {len(items)}")
    print(f"  🏅 Sports Found: {len(sports_data)}")
    if m3u8_count > 0:
        print(f"  🎬 M3U8 Extracted: {m3u8_count}")
        print(f"  ✅ Accessible: {accessible_count}")
    print(f"\n  Sports breakdown:")
    for sport, sport_items in sorted(sports_data.items()):
        icon = sport_items[0]['icon'] if sport_items else "🎯"
        m3u8_sport = sum(1 for i in sport_items if 'playable_link' in i and i['playable_link'].get('m3u8_url'))
        if m3u8_sport > 0:
            print(f"    {icon} {sport}: {len(sport_items)} events ({m3u8_sport} with M3U8)")
        else:
            print(f"    {icon} {sport}: {len(sport_items)} events")
    print(f"\n  💾 Data saved to: {output_file}")
    print("="*60 + "\n")
    
    # Create HTML only if requested
    create_html = os.getenv('CREATE_HTML', 'false').lower() == 'true'
    if create_html:
        html_content = generate_html(output_data)
        with open('streambtw_data.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        print("  📄 HTML view saved to: streambtw_data.html\n")

def generate_html(data: Dict[str, Any]) -> str:
    """Generate a simple HTML view of the data"""
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>StreamBTW Sports Data</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .sport-section {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .sport-title {{
            font-size: 24px;
            margin-bottom: 15px;
            color: #667eea;
        }}
        .event {{
            padding: 15px;
            border-left: 3px solid #667eea;
            margin-bottom: 10px;
            background: #f9f9f9;
        }}
        .event-title {{
            font-weight: bold;
            margin-bottom: 5px;
        }}
        .event-link {{
            color: #667eea;
            text-decoration: none;
            font-size: 14px;
        }}
        .event-link:hover {{
            text-decoration: underline;
        }}
        .updated {{
            color: #666;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🏆 StreamBTW Sports Data</h1>
        <p class="updated">Last updated: {data['last_updated']}</p>
    </div>
    
    <div class="stats">
        <div class="stat-card">
            <h3>📦 Total Events</h3>
            <h2>{data['total_items']}</h2>
        </div>
        <div class="stat-card">
            <h3>🏅 Sports Categories</h3>
            <h2>{data['sports_count']}</h2>
        </div>
    </div>
"""
    
    for sport, items in sorted(data['by_sport'].items()):
        icon = items[0]['icon'] if items else "🎯"
        html += f"""
    <div class="sport-section">
        <h2 class="sport-title">{icon} {sport} ({len(items)} events)</h2>
"""
        for item in items:
            html += f"""
        <div class="event">
            <div class="event-title">{item['title']}</div>
            <a href="{item['link']}" class="event-link" target="_blank">Watch Stream →</a>
        </div>
"""
        html += "    </div>\n"
    
    html += """
</body>
</html>"""
    return html

if __name__ == "__main__":
    main()
