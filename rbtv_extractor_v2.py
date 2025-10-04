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
        
        # If no matches found, try the example match URL
        if len(self.matches) == 0:
            print("\n[1b/3] No matches found, trying example match...")
            self._try_example_match()
        
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
    
    def _try_example_match(self):
        """Try the example match URL you provided"""
        try:
            example_url = "https://genegc02.ya8z6nutsz3jhbtmail.shop/football/japanese-j1-league-4105537/albirex-niigata-vs-fagiano-okayama.html"
            print(f"  Fetching: {example_url}")
            
            headers = {
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": self.api_patterns["main_site"],
            }
            
            response = scraper.get(example_url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                print(f"    ✓ Page loaded successfully")
                
                # Save sample HTML for analysis
                with open("data/sample_match_page.html", "w", encoding="utf-8") as f:
                    f.write(response.text[:50000])  # First 50KB
                print(f"    ✓ Saved sample HTML")
                
                # Parse the page
                matches = self._parse_matches_from_html(response.text, "Football")
                if matches:
                    self.matches.extend(matches)
                    print(f"    ✓ Extracted {len(matches)} matches")
                
                # Look for API calls in the HTML/JavaScript
                api_patterns = re.findall(r'https?://[a-zA-Z0-9.-]+\.[a-z]{2,}/[^"\'\s]+', response.text)
                unique_apis = list(set(api_patterns))[:20]  # Get unique APIs
                
                if unique_apis:
                    print(f"    Found {len(unique_apis)} API patterns in page:")
                    for api in unique_apis[:5]:
                        print(f"      - {api}")
                    self.api_patterns["discovered_from_page"] = unique_apis
            else:
                print(f"    ✗ Status {response.status_code}")
                
        except Exception as e:
            print(f"    ✗ Error: {e}")
    
    def _scrape_main_site(self):
        """Scrape the main site for match listings"""
        print("\n[1/3] Scraping main site for matches...")
        
        base_url = self.api_patterns["main_site"]
        
        # Try different sport categories with .html extension
        categories = [
            ("football", "Football"),
            ("basketball", "Basketball"),
            ("tennis", "Tennis"),
            ("baseball", "Baseball"),
            ("", "Home"),  # Also try home page
        ]
        
        for cat_slug, cat_name in categories:
            try:
                # Construct URL with .html extension
                if cat_slug:
                    url = f"{base_url}/{cat_slug}.html"
                else:
                    url = base_url
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
        
        # Look for match URLs with various patterns
        patterns = [
            r'/([a-z-]+)/([a-z0-9-]+)-(\d+)/([^"\']+?)\.html',  # Full match URL
            r'league-(\d+)',  # League ID
            r'match[/-](\d+)',  # Match ID
            r'id[=:](\d+)',  # ID parameter
        ]
        
        match_data = {}
        
        for pattern in patterns:
            matches_found = re.findall(pattern, html)
            for match in matches_found:
                if isinstance(match, tuple):
                    # Extract ID from tuple
                    match_id = None
                    for item in match:
                        if item.isdigit():
                            match_id = item
                            break
                    if match_id:
                        match_data[match_id] = match
                elif match.isdigit():
                    match_data[match] = match
        
        # Look for match titles separately
        title_patterns = [
            r'<[^>]*title[^>]*>([^<]*vs[^<]*)</[^>]*>',
            r'<[^>]*>([A-Za-z\s]+\s+vs\s+[A-Za-z\s]+)</[^>]*>',
            r'alt=["\']([^"\']*vs[^"\']*)["\']',
        ]
        
        titles = []
        for pattern in title_patterns:
            titles.extend(re.findall(pattern, html, re.IGNORECASE))
        
        # Build match list
        for idx, (match_id, data) in enumerate(match_data.items()):
            match = {
                "match_id": int(match_id),
                "category": category,
                "title": titles[idx] if idx < len(titles) else f"Match {match_id}",
            }
            
            # Try to construct the URL
            if isinstance(data, tuple) and len(data) >= 4:
                match["url"] = f"{self.api_patterns['main_site']}/{data[0]}/{data[1]}-{data[2]}/{data[3]}.html"
            else:
                match["url"] = f"{self.api_patterns['main_site']}/match-{match_id}.html"
            
            matches.append(match)
        
        return matches
    
    def _discover_api_endpoints(self):
        """Try to discover API endpoints"""
        print("\n[2/3] Discovering API endpoints...")
        
        api_base = self.api_patterns["api_base"]
        api_token = self.api_patterns["api_token"]
        
        # Test various API endpoint patterns
        endpoints_to_test = [
            # With token prefix
            f"{api_base}/{api_token}/api/match/list",
            f"{api_base}/{api_token}/api/match/detail",
            f"{api_base}/{api_token}/api/live/list",
            f"{api_base}/{api_token}/api/category/list",
            f"{api_base}/{api_token}/api/channel/list",
            # Without token prefix
            f"{api_base}/api/match/list",
            f"{api_base}/api/live/list",
            f"{api_base}/api/match/detail",
            # Alternative paths
            f"{api_base}/{api_token}/match/list",
            f"{api_base}/{api_token}/live",
            f"{api_base}/{api_token}/channels",
            # Try the exact endpoint pattern from your example
            f"{api_base}/{api_token}/api/match/detail?matchId=4105537&sportType=1&language=0&stream=true",
        ]
        
        working_endpoints = []
        
        for endpoint in endpoints_to_test:
            try:
                print(f"  Testing: {endpoint}")
                
                headers = {
                    "User-Agent": self.user_agent,
                    "Accept": "application/json",
                    "Referer": self.api_patterns["main_site"],
                    "Origin": self.api_patterns["main_site"],
                }
                
                response = scraper.get(endpoint, headers=headers, timeout=10)
                
                print(f"    Status: {response.status_code}")
                
                if response.status_code == 200:
                    print(f"    ✓ Endpoint working!")
                    working_endpoints.append(endpoint)
                    try:
                        data = response.json()
                        print(f"    Response type: {type(data)}")
                        if isinstance(data, dict):
                            print(f"    Keys: {list(data.keys())[:10]}")
                        self._process_api_data(data, endpoint)
                    except Exception as e:
                        print(f"    ⚠ Could not parse JSON: {e}")
                        # Try to extract match IDs from response text
                        match_ids = re.findall(r'"(?:match_?id|id)":\s*(\d+)', response.text)
                        if match_ids:
                            print(f"    Found {len(set(match_ids))} potential match IDs")
                elif response.status_code == 403:
                    print(f"    ✗ Forbidden (may need authentication)")
                elif response.status_code == 404:
                    print(f"    ✗ Not found")
                else:
                    print(f"    ✗ Unexpected status")
                
                time.sleep(1)
                
            except Exception as e:
                print(f"    ✗ Error: {e}")
        
        if working_endpoints:
            print(f"\n  ✓ Found {len(working_endpoints)} working endpoints")
            self.api_patterns["working_endpoints"] = working_endpoints
    
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
