import base64
import uuid
import os
import time
import json
import struct
from itertools import chain

# Try to import cloudscraper first, fall back to requests
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
    print("⚠ cloudscraper not available, using requests (may be blocked by Cloudflare)")

try:
    from Cryptodome.Cipher import AES
    from Cryptodome.Util.Padding import pad, unpad
except:
    try:
        from Crypto.Cipher import AES
        from Crypto.Util.Padding import pad, unpad
    except:
        pass


class RBTVExtractor:
    json_config = {}
    config_url = "https://api.backendless.com/A73E1615-C86F-F0EF-FFDC-58ED0DFC6B00/7B3DFBA7-F6CE-EDB8-FF0F-45195CF5CA00/binary"
    
    # More realistic mobile user agent
    user_agent = "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
    app_user_agent = "Dalvik/2.1.0 (Linux; U; Android 10; SM-G973F Build/QP1A.190711.020)"
    
    # Additional domains to try
    domains = [
        "rbtv.com",
        "www.fctv33.buzz",
        "genegc02.ya8z6nutsz3jhbtmail.shop",
        "rbtvplus06.com",
        "rbtvplus.com",
        "fctv33.com",
        "fctv33.net",
        "rbsports77.lat"
    ]
    
    # Multiple API endpoints to try
    api_endpoints = [
        "https://www.whatyousee.info/rbtv/3/",
        "https://www.alpharomo.com/rbtv/3/",
        "https://api.rbtv.com/v3/",
        "https://www.fctv33.buzz/api/",
        "https://genegc02.ya8z6nutsz3jhbtmail.shop/api/",
        "https://rbtvplus06.com/api/",
        "https://fctv33.com/api/",
        "https://rbsports77.lat/api/",
    ]
    
    # Fallback configurations
    fallback_configs = [
        {
            "api_url": "https://www.whatyousee.info/rbtv/3/",
            "api_referer": "https://www.whatyousee.info/",
            "api_authorization": "Basic cmVkYm94OlNlY3VyZUFQSTE5MjE2OA==",
        },
        {
            "api_url": "https://genegc02.ya8z6nutsz3jhbtmail.shop/rbtv/3/",
            "api_referer": "https://genegc02.ya8z6nutsz3jhbtmail.shop/",
            "api_authorization": "Basic cmVkYm94OlNlY3VyZUFQSTE5MjE2OA==",
        },
        {
            "api_url": "https://www.fctv33.buzz/rbtv/3/",
            "api_referer": "https://www.fctv33.buzz/",
            "api_authorization": "Basic cmVkYm94OlNlY3VyZUFQSTE5MjE2OA==",
        },
        {
            "api_url": "https://rbtvplus06.com/rbtv/3/",
            "api_referer": "https://rbtvplus06.com/",
            "api_authorization": "Basic cmVkYm94OlNlY3VyZUFQSTE5MjE2OA==",
        },
        {
            "api_url": "https://fctv33.com/rbtv/3/",
            "api_referer": "https://fctv33.com/",
            "api_authorization": "Basic cmVkYm94OlNlY3VyZUFQSTE5MjE2OA==",
        }
    ]

    def __init__(self):
        self.name = "RBTV"

    def extract_all_data(self):
        """Main method to extract all data"""
        # Try to fetch config from Backendless
        config_fetched = False
        backendless_config = None
        
        try:
            print("Attempting to fetch config from Backendless API...")
            self.__fetch_config_from_backendless()
            backendless_config = self.json_config.copy()
            
            # Test if the config URL actually works
            test_url = self.json_config.get("api_url", "") + "adduserinfo.nettv/"
            print(f"Testing Backendless config URL: {test_url}")
            test_headers = {
                "User-Agent": self.app_user_agent,
                "Accept": "application/json",
            }
            try:
                test_response = scraper.get(test_url, headers=test_headers, timeout=5)
                if test_response.status_code < 500:
                    config_fetched = True
                    print("✓ Backendless config is working")
                else:
                    print(f"✗ Backendless config returned {test_response.status_code}")
            except Exception as e:
                print(f"✗ Backendless config URL is not reachable: {e}")
        except Exception as e:
            print(f"✗ Backendless API failed: {e}")
        
        # If Backendless config didn't work, try all fallback configs
        if not config_fetched:
            print("\nBackendless config failed, trying fallback configurations...")
            for idx, fallback in enumerate(self.fallback_configs):
                try:
                    print(f"\n[Fallback {idx+1}/{len(self.fallback_configs)}]")
                    print(f"  Testing: {fallback['api_url']}")
                    self.json_config = fallback.copy()
                    
                    # Test user registration endpoint
                    test_url = fallback['api_url'] + "adduserinfo.nettv/"
                    test_headers = {
                        "User-Agent": self.app_user_agent,
                        "Accept": "application/json",
                        "Referer": fallback['api_referer'],
                        "Authorization": fallback['api_authorization'],
                    }
                    
                    test_response = scraper.get(test_url, headers=test_headers, timeout=10)
                    if test_response.status_code < 500:
                        print(f"  ✓ Fallback config #{idx+1} is reachable (status: {test_response.status_code})")
                        config_fetched = True
                        break
                    else:
                        print(f"  ✗ Returned status: {test_response.status_code}")
                except Exception as e:
                    print(f"  ✗ Failed: {e}")
                    continue
        
        if not config_fetched:
            raise Exception("Could not find any working API configuration. All endpoints are blocked or unreachable.")
        
        print(f"\n{'='*60}")
        print(f"Using API: {self.json_config.get('api_url', 'Unknown')}")
        print(f"{'='*60}\n")
        
        # Register user
        self.__register_user()
        
        # Fetch videos
        self.__fetch_videos()
        
        self.json_config["data_age"] = time.time()
        self.json_config["extraction_date"] = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
        self.json_config["domains"] = self.domains
        
        return self.json_config

    def __fetch_config_from_backendless(self):
        """Fetch config from Backendless REST API"""
        # Try REST API endpoint
        rest_url = "https://api.backendless.com/A73E1615-C86F-F0EF-FFDC-58ED0DFC6B00/7B3DFBA7-F6CE-EDB8-FF0F-45195CF5CA00/data/AppConfigHotel"
        
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://backendless.com/",
        }
        
        resp = scraper.get(rest_url, headers=headers, timeout=15)
        resp.raise_for_status()
        
        data = resp.json()
        if isinstance(data, list) and len(data) > 0:
            amf_data = data[0]
            self.__parse_config_data(amf_data)
        else:
            raise Exception("No config data returned from Backendless")

    def __parse_config_data(self, amf_data):
        """Parse configuration data from API response"""
        try:
            self.json_config["api_url"] = self.__decode_value(amf_data.get("YmFzZXVybG5ld3gw", ""))
            self.json_config["api_referer"] = self.__decode_value(amf_data.get("SXNpc2VrZWxvX3Nlc2lzdGltdV95ZXppbm9tYm9sbzAw", ""))
            self.json_config["api_authorization"] = self.__decode_value(amf_data.get("amFnX3Ryb3JfYXR0X2Vu", ""))
            self.json_config["token_url_21"] = self.__decode_value(amf_data.get("Y2FsYWFtb19pa3Mw", ""))
            self.json_config["token_auth_21"] = self.__decode_value(amf_data.get("WXJfd3lmX3luX2JhaXMw", ""))
            self.json_config["token_url_38"] = self.__decode_value(amf_data.get("YmVsZ2lfMzgw", ""))
            self.json_config["token_auth_38"] = self.__decode_value(amf_data.get("Z2Vsb29mc2JyaWVm", ""))
            self.json_config["token_url_48"] = self.__decode_value(amf_data.get("Ym9ya3lsd3VyXzQ4", ""))
            self.json_config["token_auth_48"] = self.__decode_value(amf_data.get("dGVydHRleWFj", ""))
            self.json_config["mod_value"] = self.__decode_value(amf_data.get("TW9vbl9oaWsx", ""))
        except Exception as e:
            print(f"Warning: Error parsing some config fields: {e}")

    def __register_user(self):
        """Register a new user"""
        data = {
            "gmail": "",
            "api_level": "28",
            "android_id": uuid.uuid4().hex[:16],
            "device_id": "unknown",
            "device_name": "Amazon AFTKA",
            "version": "2.3 (41)",
        }
        
        endpoint = self.json_config.get("api_url", "") + "adduserinfo.nettv/"
        
        print(f"Registering user at: {endpoint}")
        
        try:
            result = self.__api_request(endpoint, data)
            user_id = result.get("user_id")
            
            if not user_id:
                # Try to extract from response
                if isinstance(result, dict):
                    user_id = result.get("id") or result.get("userId") or str(int(time.time() * 1000))
                else:
                    user_id = str(int(time.time() * 1000))
            
            self.json_config["user"] = {"user_id": str(user_id), "check": 41}
            print(f"✓ User registered with ID: {user_id}")
            return
            
        except Exception as e:
            print(f"⚠ User registration failed: {e}")
        
        # Generate fallback user_id
        print("⚠ Using generated user ID")
        self.json_config["user"] = {"user_id": str(int(time.time() * 1000)), "check": 41}

    def __fetch_videos(self):
        """Fetch all videos, categories, and countries"""
        data = {
            "check": self.json_config["user"]["check"],
            "user_id": self.json_config["user"]["user_id"],
            "version": "41",
        }
        
        # Add hash_id if crypto is available
        try:
            data["hash_id"] = self.enc_aes_cbc_single(
                f'{self.json_config["user"]["user_id"]}_wdufherfbweicerwf',
                f'{self.json_config["user"]["user_id"]}cefrecdce'.encode("utf-8")[:16],
                f'{self.json_config["user"]["user_id"]}cwefervwv'.encode("utf-8")[:16],
            )
        except Exception as e:
            print(f"Warning: Could not generate hash_id: {e}")
        
        endpoint = self.json_config.get("api_url", "") + "redbox.tv/"
        
        print(f"Fetching videos from: {endpoint}")
        res = self.__api_request(endpoint, data)
        
        # Parse categories
        categories = []
        try:
            categories = [
                {"category_id": item["cat_id"], "title": item["cat_name"]} 
                for item in res.get("categories_list", [])
            ]
        except Exception as e:
            print(f"Warning: Could not parse categories: {e}")
        
        # Parse countries
        countries = []
        try:
            countries = [
                {"country_id": item["country_id"], "title": item["country_name"]} 
                for item in res.get("countries_list", [])
            ]
        except Exception as e:
            print(f"Warning: Could not parse countries: {e}")
        
        # Parse videos/channels
        videos = []
        channels_key = "eY2hhbm5lbHNfbGlzdA=="
        
        # Try different possible keys
        possible_keys = [channels_key, "channels_list", "channels", "videos"]
        channels_data = None
        
        for key in possible_keys:
            if key in res:
                channels_data = res[key]
                print(f"Found channels data under key: {key}")
                break
        
        if not channels_data:
            print(f"Available keys in response: {list(res.keys())}")
            raise Exception("Could not find channels data in response")
        
        for item in channels_data:
            try:
                # Try to decode video_id
                video_id_encoded = item.get("rY19pZA==", item.get("c_id", item.get("id", "")))
                try:
                    video_id = int(self.__decode_value2(video_id_encoded))
                except:
                    video_id = int(video_id_encoded) if str(video_id_encoded).isdigit() else hash(str(video_id_encoded))
                
                # Try to decode name
                name_encoded = item.get("ZY19uYW1l", item.get("c_name", item.get("name", "Unknown")))
                try:
                    title = self.__decode_value2(name_encoded)
                except:
                    title = str(name_encoded)
                
                # Try to decode logo
                logo_encoded = item.get("abG9nb191cmw=", item.get("logo_url", item.get("logo", "")))
                try:
                    logo_url = self.__decode_value(logo_encoded)
                except:
                    logo_url = str(logo_encoded)
                
                video = {
                    "video_id": video_id,
                    "category": item.get("cat_id", ""),
                    "country": item.get("country_id", ""),
                    "title": title,
                    "logo_url": logo_url,
                    "streams": []
                }
                
                # Parse streams
                streams_key = item.get("Qc3RyZWFtX2xpc3Q=", item.get("stream_list", item.get("streams", [])))
                for stream in streams_key if isinstance(streams_key, list) else []:
                    try:
                        stream_obj = {
                            "stream_id": self.__safe_decode2(stream.get("cc3RyZWFtX2lk", stream.get("stream_id", ""))),
                            "video_id": video_id,
                            "token": int(self.__safe_decode2(stream.get("AdG9rZW4=", stream.get("token", "0")))),
                            "stream_url": self.__safe_decode(stream.get("Bc3RyZWFtX3VybA==", stream.get("stream_url", ""))),
                        }
                        video["streams"].append(stream_obj)
                    except Exception as e:
                        print(f"Warning: Failed to parse stream: {e}")
                        continue
                
                videos.append(video)
                
            except Exception as e:
                print(f"Warning: Failed to parse video item: {e}")
                continue
        
        self.json_config["categories"] = categories
        self.json_config["countries"] = countries
        self.json_config["videos"] = videos
        self.json_config["total_videos"] = len(videos)
        self.json_config["total_categories"] = len(categories)
        self.json_config["total_countries"] = len(countries)
        
        print(f"✓ Parsed {len(videos)} videos, {len(categories)} categories, {len(countries)} countries")

    def __api_request(self, url, data):
        """Make API request with headers"""
        headers = {
            "User-Agent": self.app_user_agent,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": self.json_config.get("api_referer", "https://www.whatyousee.info/"),
            "Authorization": self.json_config.get("api_authorization", "Basic cmVkYm94OlNlY3VyZUFQSTE5MjE2OA=="),
            "Origin": self.json_config.get("api_referer", "https://www.whatyousee.info/").rstrip('/'),
            "Connection": "keep-alive",
            "DNT": "1",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }
        
        # Add a small delay to avoid rate limiting
        time.sleep(1.5)
        
        try:
            r = scraper.post(url, headers=headers, data=data, timeout=20)
            
            # Log the response for debugging
            print(f"  Response status: {r.status_code}")
            
            # If we get 403, it might be Cloudflare - try with different approach
            if r.status_code == 403:
                print(f"  Got 403 Forbidden - trying alternate method...")
                # Try without some headers that might trigger WAF
                simple_headers = {
                    "User-Agent": self.app_user_agent,
                    "Accept": "application/json",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Referer": self.json_config.get("api_referer", ""),
                    "Authorization": self.json_config.get("api_authorization", ""),
                }
                time.sleep(2)
                r = scraper.post(url, headers=simple_headers, data=data, timeout=20)
                print(f"  Retry response status: {r.status_code}")
            
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"  API request failed: {e}")
            raise

    def __safe_decode(self, v):
        """Safely decode base64 value (skip first character)"""
        try:
            return self.__decode_value(v)
        except:
            return str(v) if v else ""

    def __safe_decode2(self, v):
        """Safely decode base64 value (skip last character)"""
        try:
            return self.__decode_value2(v)
        except:
            return str(v) if v else ""

    def __decode_value(self, v):
        """Decode base64 value (skip first character)"""
        if not v or not isinstance(v, str):
            return str(v) if v else ""
        try:
            return base64.b64decode(v[1:]).decode("utf-8")
        except:
            return str(v)

    def __decode_value2(self, v):
        """Decode base64 value (skip last character)"""
        if not v or not isinstance(v, str):
            return str(v) if v else ""
        try:
            return base64.b64decode(v[:-1]).decode("utf-8")
        except:
            return str(v)

    def enc_aes_cbc_single(self, msg, key, iv):
        """Encrypt message using AES CBC"""
        cipher = AES.new(key, AES.MODE_CBC, iv=iv)
        return base64.b64encode(cipher.encrypt(pad(msg.encode("utf-8"), 16))).decode("utf-8")


def main():
    """Main execution function"""
    print("=" * 60)
    print("RBTV Data Extractor")
    print("=" * 60)
    
    # Disable SSL warnings
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    extractor = RBTVExtractor()
    
    try:
        data = extractor.extract_all_data()
        
        # Create data directory if it doesn't exist
        os.makedirs("data", exist_ok=True)
        
        # Save full data
        print("\nSaving data files...")
        with open("data/rbtv_data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print("✓ Saved: data/rbtv_data.json")
        
        # Create a summary file
        summary = {
            "extraction_date": data["extraction_date"],
            "total_videos": data["total_videos"],
            "total_categories": data["total_categories"],
            "total_countries": data["total_countries"],
            "domains": data["domains"],
            "api_url": data.get("api_url", "Unknown")
        }
        
        with open("data/summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        print("✓ Saved: data/summary.json")
        
        # Create channels list (simplified)
        channels = [{
            "id": video["video_id"],
            "title": video["title"],
            "category": video["category"],
            "country": video["country"],
            "logo": video["logo_url"],
            "streams_count": len(video["streams"])
        } for video in data["videos"]]
        
        with open("data/channels.json", "w", encoding="utf-8") as f:
            json.dump(channels, f, indent=2, ensure_ascii=False)
        print("✓ Saved: data/channels.json")
        
        print("\n" + "=" * 60)
        print("EXTRACTION SUMMARY")
        print("=" * 60)
        print(f"Total Videos:     {data['total_videos']}")
        print(f"Total Categories: {data['total_categories']}")
        print(f"Total Countries:  {data['total_countries']}")
        print(f"API URL:          {data.get('api_url', 'Unknown')}")
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
