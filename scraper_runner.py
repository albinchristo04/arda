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
    
    # Try different possible domains
    possible_domains = ["720pstream.lc", "https://720pstream.lc/", "720pstream.lc", "720pstream.ic"]
    base_url = None
    
    for domain in possible_domains:
        try:
            test_url = f"http://{domain}"
            print(f"Trying domain: {domain}")
            r = requests.get(test_url, timeout=5)
            if r.status_code == 200:
                base_url = test_url
                print(f"Successfully connected to: {domain}")
                break
        except:
            continue
    
    if not base_url:
        print("Could not connect to any 720pstream domain")
        return []
    
    try:
        r = requests.get(base_url, timeout=10).text
        soup = BeautifulSoup(r, "html.parser")
        
        for li in soup.select("li.nav-item"):
            league = li.text.strip()
            icon_tag = li.find("img")
            icon = icon_tag.get("src") if icon_tag else None
            
            a_tag = li.find("a")
            if not a_tag:
                continue
                
            href = base_url + a_tag.get("href")
            
            try:
                r_league = requests.get(href, timeout=10).text
                soup_league = BeautifulSoup(r_league, "html.parser")
                
                for game in soup_league.select("a.btn"):
                    title_tag = game.select_one("span.text-success")
                    game_title = title_tag.text if title_tag else "Unknown"
                    
                    img_tag = game.select_one("img")
                    game_icon = img_tag.get("src") if img_tag else None
                    
                    game_href = base_url + game.get("href")
                    
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
                            except:
                                pass
                    
                    games.append({
                        'title': game_title,
                        'league': league,
                        'icon': game_icon,
                        'starttime': utc_time.isoformat() if utc_time else None,
                        'link': game_href
                    })
                    
            except Exception as e:
                print(f"Error fetching league {league}: {e}")
                continue
                
    except Exception as e:
        print(f"Error fetching main page: {e}")
        return []
    
    return games

def main():
    try:
        print("Starting scrape...")
        
        games = get_games()
        print(f"Found {len(games)} games")
        
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
        
    except Exception as e:
        print(f"Error during scraping: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
