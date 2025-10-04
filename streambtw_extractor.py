import requests
from bs4 import BeautifulSoup
import json
import os
import re
from datetime import datetime
from typing import List, Dict, Any, Optional

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
    
    def find_iframes(self, url: str) -> List[str]:
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
                    iframes.append(src)
            
            # Also check for iframes in script tags
            for script in soup.find_all("script"):
                if script.string:
                    # Look for iframe URLs in JavaScript
                    iframe_matches = re.findall(r'(?:iframe|src)[\s]*[=:][\s]*["\']([^"\']+)["\']', script.string)
                    for match in iframe_matches:
                        if match.startswith("http"):
                            iframes.append(match)
            
            return iframes
        except Exception as e:
            print(f"Error finding iframes: {e}")
            return []
    
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
    
    def get_link_details(self, url: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific link including iframes"""
        try:
            print(f"  🔗 Extracting iframes from: {url}")
            
            iframes = self.find_iframes(url)
            
            if iframes:
                return {
                    "url": url,
                    "iframe_count": len(iframes),
                    "iframes": iframes,
                    "primary_iframe": iframes[0] if iframes else None,
                    "headers": {
                        "Origin": f"https://{self.domains[0]}",
                        "User-Agent": self.user_agent,
                        "Referer": url
                    }
                }
            else:
                return {
                    "url": url,
                    "iframe_count": 0,
                    "iframes": [],
                    "primary_iframe": None
                }
        except Exception as e:
            print(f"    ❌ Error: {e}")
            return None

def main():
    print("="*60)
    print("🏆 StreamBTW Sports Streaming Extractor")
    print("="*60 + "\n")
    
    extractor = StreamBTWExtractor()
    
    # Extract all items
    items = extractor.get_items()
    
    # Optionally extract iframe details for each link
    extract_iframes = os.getenv('EXTRACT_IFRAMES', 'false').lower() == 'true'
    
    if extract_iframes and items:
        print(f"\n🔍 Extracting iframe details for {len(items)} links...")
        for idx, item in enumerate(items, 1):
            if item.get('link'):
                print(f"\n[{idx}/{len(items)}] Processing: {item['title']}")
                link_details = extractor.get_link_details(item['link'])
                if link_details:
                    item['link_details'] = link_details
    
    # Organize by sport
    sports_data = {}
    for item in items:
        sport = item['sport']
        if sport not in sports_data:
            sports_data[sport] = []
        sports_data[sport].append(item)
    
    # Prepare output
    output_data = {
        "extractor": "StreamBTW",
        "last_updated": datetime.utcnow().isoformat(),
        "total_items": len(items),
        "sports_count": len(sports_data),
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
    print(f"\n  Sports breakdown:")
    for sport, sport_items in sorted(sports_data.items()):
        icon = sport_items[0]['icon'] if sport_items else "🎯"
        print(f"    {icon} {sport}: {len(sport_items)} events")
    print(f"\n  💾 Data saved to: {output_file}")
    print("="*60 + "\n")
    
    # Create a simple HTML view (optional)
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
