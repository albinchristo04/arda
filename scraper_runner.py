import json
import sys
import os
import requests
import re
import time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

def get_games():
    """Scrape games from 720pstream"""
    games = []
    
    # Try different possible domains with HTTPS
    possible_domains = ["720pstream.lc", "720pstream.nu", "720pstream.me", "720pstream.ic"]
    base_url = None
    
    for domain in possible_domains:
        try:
            # Use HTTPS instead of HTTP
            test_url = f"https://{domain}"
            print(f"Trying domain: {domain}")
            
            # Add headers to mimic a browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
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
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
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
            # Handle both relative and absolute URLs
            if href.startswith("http"):
                full_href = href
            else:
                full_href = base_url + href if not href.startswith("/") else base_url + href
            
            try:
                r_league = requests.get(full_href, timeout=15, headers=headers).text
                soup_league = BeautifulSoup(r_league, "html.parser")
                
                for game in soup_league.select("a.btn"):
                    title_tag = game.select_one("span.text-success")
                    game_title = title_tag.text.strip() if title_tag else "Unknown"
                    
                    img_tag = game.select_one("img")
                    game_icon = img_tag.get("src") if img_tag else None
                    
                    game_href_raw = game.get("href")
                    if game_href_raw.startswith("http"):
                        game_href = game_href_raw
                    else:
                        game_href = base_url + game_href_raw if not game_href_raw.startswith("/") else base_url + game_href_raw
                    
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
                                print(f"Error parsing time: {e}")
                                pass
                    
                    games.append({
                        'title': game_title,
                        'league': league,
                        'icon': game_icon,
                        'starttime': utc_time.isoformat() if utc_time else None,
                        'link': game_href
                    })
                
                print(f"Found {len(games)} games so far from {league}")
                    
            except Exception as e:
                print(f"Error fetching league {league}: {e}")
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
            leagues = set(game['league'] for game in games)
            print(f"Leagues found: {', '.join(leagues)}")
        
    except Exception as e:
        print(f"Error during scraping: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
