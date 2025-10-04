import json
import os
import time
import re
from urllib.parse import urlparse, parse_qs

try:
    import cloudscraper
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'android',
            'mobile': True,
        }
    )
    print("✓ Using cloudscraper for Cloudflare bypass")
except ImportError:
    import requests
    scraper = requests.Session()
    print("⚠ cloudscraper not available, using requests")


class RBTVExtractorV2:
    """
    Updated RBTV extractor based on actual API endpoints discovered
    """
    
    def __init__(self):
        self.name = "RBTV"
        self.user_agent = "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
        
        # Discovered domains
        self.domains = [
            "genegc02.ya8z6nutsz3jhbtmail.shop",
            "apis-data10.tcgfs39a2.xyz",
            "fhlsport200.tbafs39a1.xyz",
            "www.fctv33.buzz",
            "rbtvplus06.com",
            "fctv33.com",
            "rbsports77.lat"
        ]
        
        # Known API patterns
        self.api_patterns = {
            "main_site": "https://genegc02.ya8z6nutsz3jhbtmail.shop",
            "api_base": "https://apis-data10.tcgfs39a2.xyz",
            "api_token": "sfverc600ec442d9da1c9bfdc814df10b919d5f44d1",
            "stream_base": "https://fhlsport200.tbafs39a1.xyz"
        }
        
        self.matches = []
        self.categories = []
        
    def extract_all_data(self):
        """Main extraction method"""
        print("Starting data extraction from RBTV network...")
        
        # Try to scrape main site for matches
        self._scrape_main_site()
        
        # Try to discover more API endpoints
        self._discover_api_endpoints()
        
        # Build final data structure
        data = {
            "extraction_date": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "data_age": time.time(),
            "domains": self.domains,
            "api_patterns": self.api_patterns,
            "total_matches": len(self.matches),
            "total_categories": len(self.categories),
            "matches": self.matches,
            "categories": self.categories,
        }
        
        return data
    
    def _scrape_main_site(self):
        """Scrape the main site for match listings"""
        print("\n[1/3] Scraping main site for matches...")
        
        base_url = self.api_patterns["main_site"]
        
        # Try different sport categories
        categories = [
            ("football", "Football"),
            ("basketball", "Basketball"),
            ("tennis", "Tennis"),
            ("baseball", "Baseball"),
        ]
        
        for cat_slug, cat_name in categories:
            try:
                url = f"{base_url}/{cat_slug}"
                print(f"  Fetching: {url}")
                
                headers = {
                    "User-Agent": self.user_agent,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Referer": base_url,
                }
                
                response = scraper.get(url, headers=headers, timeout=15)
                
                if response.status_code == 200:
                    # Extract match IDs and info from HTML
                    matches = self._parse_matches_from_html(response.text, cat_name)
                    self.matches.extend(matches)
                    print(f"    ✓ Found {len(matches)} matches in {cat_name}")
                    
                    if cat_name not in [c["name"] for c in self.categories]:
                        self.categories.append({
                            "name": cat_name,
                            "slug": cat_slug,
                            "count": len(matches)
                        })
                else:
                    print(f"    ✗ Status {response.status_code}")
                
                time.sleep(1)  # Be polite
                
            except Exception as e:
                print(f"    ✗ Error: {e}")
                continue
    
    def _parse_matches_from_html(self, html, category):
        """Parse match information from HTML"""
        matches = []
        
        # Look for match IDs in URLs
        match_id_pattern = r'(?:match|league)-(\d+)'
        match_ids = re.findall(match_id_pattern, html)
        
        # Look for match names/titles
        title_pattern = r'<a[^>]*>([^<]+vs[^<]+)</a>'
        titles = re.findall(title_pattern, html, re.IGNORECASE)
        
        # Combine findings
        for i, match_id in enumerate(set(match_ids)):
            match = {
                "match_id": int(match_id),
                "category": category,
                "title": titles[i] if i < len(titles) else f"Match {match_id}",
                "url": f"{self.api_patterns['main_site']}/match-{match_id}/",
            }
            matches.append(match)
        
        return matches
    
    def _discover_api_endpoints(self):
        """Try to discover API endpoints"""
        print("\n[2/3] Discovering API endpoints...")
        
        api_base = self.api_patterns["api_base"]
        api_token = self.api_patterns["api_token"]
        
        # Test API endpoints
        endpoints_to_test = [
            f"{api_base}/{api_token}/api/match/list",
            f"{api_base}/{api_token}/api/live/list",
            f"{api_base}/{api_token}/api/category/list",
            f"{api_base}/{api_token}/api/channel/list",
        ]
        
        for endpoint in endpoints_to_test:
            try:
                print(f"  Testing: {endpoint}")
                
                headers = {
                    "User-Agent": self.user_agent,
                    "Accept": "application/json",
                    "Referer": self.api_patterns["main_site"],
                }
                
                response = scraper.get(endpoint, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    print(f"    ✓ Endpoint working!")
                    try:
                        data = response.json()
                        self._process_api_data(data, endpoint)
                    except:
                        print(f"    ⚠ Response is not JSON")
                else:
                    print(f"    ✗ Status {response.status_code}")
                
                time.sleep(1)
                
            except Exception as e:
                print(f"    ✗ Error: {e}")
    
    def _process_api_data(self, data, endpoint):
        """Process data from API endpoints"""
        if isinstance(data, dict):
            # Look for match/channel lists
            for key in ['matches', 'channels', 'data', 'list', 'results']:
                if key in data and isinstance(data[key], list):
                    print(f"    Found {len(data[key])} items in '{key}'")
                    
                    for item in data[key][:5]:  # Sample first 5
                        if isinstance(item, dict):
                            match_info = {
                                "match_id": item.get('id') or item.get('matchId') or item.get('match_id'),
                                "title": item.get('title') or item.get('name') or item.get('match_name'),
                                "category": item.get('category') or item.get('sport') or item.get('sportType'),
                                "stream_url": item.get('stream') or item.get('streamUrl') or item.get('url'),
                            }
                            
                            if match_info['match_id']:
                                self.matches.append(match_info)
    
    def get_match_details(self, match_id):
        """Get detailed information for a specific match"""
        api_base = self.api_patterns["api_base"]
        api_token = self.api_patterns["api_token"]
        
        url = f"{api_base}/{api_token}/api/match/detail"
        
        params = {
            "matchId": match_id,
            "sportType": 1,
            "language": 0,
            "stream": "true"
        }
        
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
            "Referer": self.api_patterns["main_site"],
        }
        
        try:
            response = scraper.get(url, params=params, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Error getting match details: {e}")
        
        return None


def main():
    """Main execution function"""
    print("=" * 60)
    print("RBTV Data Extractor V2")
    print("Based on discovered API endpoints")
    print("=" * 60)
    
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    extractor = RBTVExtractorV2()
    
    try:
        data = extractor.extract_all_data()
        
        # Create data directory
        os.makedirs("data", exist_ok=True)
        
        # Save full data
        print("\n[3/3] Saving data files...")
        with open("data/rbtv_data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print("✓ Saved: data/rbtv_data.json")
        
        # Create summary
        summary = {
            "extraction_date": data["extraction_date"],
            "total_matches": data["total_matches"],
            "total_categories": data["total_categories"],
            "domains": data["domains"],
            "api_patterns": data["api_patterns"]
        }
        
        with open("data/summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        print("✓ Saved: data/summary.json")
        
        # Create matches list
        if data["matches"]:
            with open("data/matches.json", "w", encoding="utf-8") as f:
                json.dump(data["matches"], f, indent=2, ensure_ascii=False)
            print("✓ Saved: data/matches.json")
        
        # Test match details API for first match
        if data["matches"]:
            print("\n" + "=" * 60)
            print("Testing Match Details API")
            print("=" * 60)
            
            first_match = data["matches"][0]
            if "match_id" in first_match and first_match["match_id"]:
                print(f"Getting details for match: {first_match['match_id']}")
                details = extractor.get_match_details(first_match["match_id"])
                
                if details:
                    with open("data/sample_match_details.json", "w", encoding="utf-8") as f:
                        json.dump(details, f, indent=2, ensure_ascii=False)
                    print("✓ Saved: data/sample_match_details.json")
        
        print("\n" + "=" * 60)
        print("EXTRACTION SUMMARY")
        print("=" * 60)
        print(f"Total Matches:    {data['total_matches']}")
        print(f"Total Categories: {data['total_categories']}")
        print(f"Extraction Date:  {data['extraction_date']}")
        print("=" * 60)
        print("✓ Extraction completed successfully!")
        
    except Exception as e:
        print("\n" + "=" * 60)
        print("ERROR")
        print("=" * 60)
        print(f"✗ Error during extraction: {str(e)}")
        import traceback
        traceback.print_exc()
        print("=" * 60)
        raise


if __name__ == "__main__":
    main()
