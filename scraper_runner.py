import json
import sys
import os
import requests
import re
import time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

def get_link(stream_page_url, headers):
    """
    Extract the actual m3u8 stream URL from a stream page
    This is the equivalent of get_link() in the Kodi addon
    """
    try:
        print(f"  Extracting stream from: {stream_page_url}")
        
        # Get the stream page
        r = requests.get(stream_page_url, timeout=15, headers=headers)
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
        
        # Make absolute URL if relative
        iframe_url = urljoin(stream_page_url, iframe_src)
        print(f"  Found iframe: {iframe_url}")
        
        # Get the iframe page content
        iframe_response = requests.get(iframe_url, timeout=15, headers=headers)
        iframe_html = iframe_response.text
        
        # Scan for m3u8 URLs using multiple patterns
        m3u8_patterns = [
            r'source:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'file:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'["\']([^"\']*\.m3u8[^"\']*)["\']',
            r'https?://[^\s<>"\']+\.m3u8[^\s<>"\']*'
        ]
        
        m3u8_url = None
        for pattern in m3u8_patterns:
            matches = re.findall(pattern, iframe_html)
            if matches:
                m3u8_url = matches[0]
                break
        
        if not m3u8_url:
            print("  No m3u8 URL found in iframe")
            return None
        
        # Make absolute URL if needed
        m3u8_url = urljoin(iframe_url, m3u8_url)
        print(f"  Found m3u8: {m3u8_url}")
        
        # Extract domain info for headers
        parsed = urlparse(m3u8_url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        
        return {
            'url': m3u8_url,
            'headers': {
                'Origin': origin,
                'Referer': iframe_url,
                'User-Agent': headers['User-Agent']
            }
        }
        
    except Exception as e:
        print(f"  Error extracting stream: {e}")
        return None

def get_games():
    """Scrape games from 720pstream"""
    games = []
    
    # Try different possible domains with HTTPS
    possible_domains = ["720pstream.lc", "720pstream.nu", "720pstream.me", "720pstream.ic"]
    base_url = None
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    for domain in possible_domains:
        try:
            test_url = f"https://{domain}"
            print(f"Trying domain: {domain}")
            
            r = requests.get(test_url, timeout=10, headers=headers, verify=True)
            if r.status_code == 200:
                base_url = test_url
                print(f"Successfully connected to: {domain}")
                break
            else:
                print(f"Failed with status code: {r.status_code}")
        except Exception as e:
            print(f"Error connecting to {domain}: {str(e)}")
            continue
    
    if not base_url:
        print("Could not connect to any 720pstream domain")
        return []
    
    try:
        r = requests.get(base_url, timeout=15, headers=headers).text
        soup = BeautifulSoup(r, "html.parser")
        
        for li in soup.select("li.nav-item"):
            league = li.text.strip()
            icon_tag = li.find("img")
            icon = icon_tag.get("src") if icon_tag else None
            
            a_tag = li.find("a")
            if not a_tag:
                continue
                
            href = a_tag.get("href")
            full_href = urljoin(base_url, href)
            
            print(f"\nProcessing league: {league}")
            
            try:
                r_league = requests.get(full_href, timeout=15, headers=headers).text
                soup_league = BeautifulSoup(r_league, "html.parser")
                
                for game in soup_league.select("a.btn"):
                    # Extract full match title (both teams)
                    title_tag = game.select_one("span.text-success")
                    if title_tag:
                        # Get the full text which should contain "Team1 vs Team2" or similar
                        game_title = title_tag.text.strip()
                    else:
                        # Fallback: try to get all text from the game button
                        game_title = game.get_text(strip=True, separator=' ')
                        # Clean up the title by removing time info
                        game_title = re.sub(r'\d{2}:\d{2}\s*(AM|PM)?', '', game_title).strip()
                    
                    img_tag = game.select_one("img")
                    game_icon = img_tag.get("src") if img_tag else None
                    if game_icon:
                        game_icon = urljoin(base_url, game_icon)
                    
                    game_href_raw = game.get("href")
                    game_href = urljoin(base_url, game_href_raw)
                    
                    # Extract time
                    game_time_tag = game.select_one("div.text-warning")
                    utc_time = None
                    
                    if game_time_tag and game_time_tag.text != "24/7":
                        time_tag = game_time_tag.find("time")
                        if time_tag:
                            time_str = time_tag.get("datetime")
                            try:
                                if "-04" in time_str:
                                    utc_time = datetime(*(time.strptime(time_str, "%Y-%m-%dT%H:%M:%S-04:00")[:6])) + timedelta(hours=4)
                                else:
                                    utc_time = datetime(*(time.strptime(time_str, "%Y-%m-%dT%H:%M:%S-05:00")[:6])) + timedelta(hours=5)
                            except Exception as e:
                                print(f"  Error parsing time: {e}")
                    
                    game_data = {
                        'title': game_title,
                        'league': league,
                        'icon': game_icon,
                        'starttime': utc_time.isoformat() if utc_time else None,
                        'link': game_href,
                        'stream_info': None
                    }
                    
                    # Extract the actual stream link (m3u8)
                    # Note: This can be slow, so you might want to do this on-demand instead
                    # For now, we'll add it but you can comment out if it's too slow
                    stream_info = get_link(game_href, headers)
                    if stream_info:
                        game_data['stream_info'] = stream_info
                    
                    games.append(game_data)
                    print(f"  Added: {game_title}")
                
                print(f"Found {len(games)} games so far")
                
                # Add a small delay to avoid overwhelming the server
                time.sleep(0.5)
                    
            except Exception as e:
                print(f"Error fetching league {league}: {e}")
                import traceback
                traceback.print_exc()
                continue
                
    except Exception as e:
        print(f"Error fetching main page: {e}")
        import traceback
        traceback.print_exc()
        return []
    
    return games

def main():
    try:
        print("Starting scrape...")
        print(f"Current time: {datetime.utcnow().isoformat()}")
        
        games = get_games()
        print(f"\n{'='*50}")
        print(f"Found {len(games)} total games")
        
        # Prepare output data
        output = {
            'timestamp': datetime.utcnow().isoformat(),
            'total_games': len(games),
            'games': games
        }
        
        # Write to JSON file
        with open('scraped_data.json', 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print("Data successfully written to scraped_data.json")
        
        # Print summary
        if games:
            leagues = {}
            streams_found = 0
            for game in games:
                leagues[game['league']] = leagues.get(game['league'], 0) + 1
                if game.get('stream_info'):
                    streams_found += 1
            
            print(f"\nLeagues summary:")
            for league, count in leagues.items():
                print(f"  {league}: {count} games")
            print(f"\nStreams extracted: {streams_found}/{len(games)}")
        
    except Exception as e:
        print(f"Error during scraping: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
