import requests
import re
import json
import os
from datetime import datetime
from typing import Optional, Dict, Any

class VoodcExtractor:
    def __init__(self):
        self.domains = ["voodc.com"]
        self.name = "Voodc"
        self.user_agent = "Mozilla/5.0 (Linux; Android 13; SM-G981B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36"
        self.timeout = 30
        
    def jsunpack_unpack(self, packed_js: str) -> str:
        """Simple JSUnpack implementation for packed JavaScript"""
        try:
            # Extract the packed data
            pattern = r"}\('(.+)',(\d+),(\d+),'(.+)'\.split\('\|'\)"
            match = re.search(pattern, packed_js)
            if not match:
                return ""
            
            payload, radix, count, symbols = match.groups()
            symbols = symbols.split('|')
            radix = int(radix)
            
            def decode(d, e, c):
                def base_decode(num, radix):
                    alphabet = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
                    result = 0
                    for char in str(num):
                        result = result * radix + alphabet.index(char)
                    return result
                
                result = payload
                for i in range(len(symbols) - 1, -1, -1):
                    if symbols[i]:
                        pattern = r'\b' + (str(i) if i < radix else f"[{chr(i//radix + 97)}]") + r'\b'
                        result = re.sub(pattern, symbols[i], result)
                return result
            
            return decode(payload, radix, len(symbols))
        except Exception as e:
            print(f"JSUnpack error: {e}")
            return ""
    
    def extract_link(self, url: str) -> Optional[Dict[str, Any]]:
        """Extract M3U8 link from Voodc URL"""
        try:
            print(f"Processing URL: {url}")
            
            # Get initial page
            r = requests.get(url, headers={"User-Agent": self.user_agent}, timeout=self.timeout)
            r.raise_for_status()
            
            # Find script URL
            script_matches = re.findall(r'" src="(.+?)"', r.text)
            if not script_matches:
                print("No script URL found")
                return None
                
            script = "https:" + script_matches[0]
            split = script.split("/")
            embed_url = f"https://voodc.com/player/d/{split[-1]}/{split[-2]}"
            
            print(f"Embed URL: {embed_url}")
            
            # Get embed page
            r = requests.get(embed_url, headers={"User-Agent": self.user_agent}, timeout=self.timeout)
            r.raise_for_status()
            
            # Try to find M3U8 directly
            re_m3u8 = re.findall(r'"file": \'(.+?)\'', r.text)
            
            if len(re_m3u8) > 0:
                m3u8 = re_m3u8[0]
                print(f"Found M3U8: {m3u8}")
            else:
                # Extract from packed JavaScript
                fid_matches = re.findall(r"fid='(.+?)'", r.text)
                if not fid_matches:
                    print("No fid found")
                    return None
                    
                fid = fid_matches[0]
                player_url = f"https://player.mycraft.click/{fid}"
                
                print(f"Player URL: {player_url}")
                
                r_player = requests.get(player_url, timeout=self.timeout)
                r_player.raise_for_status()
                
                re_packed = re.findall(r"(}\(.+)", r_player.text)
                if not re_packed:
                    print("No packed JavaScript found")
                    return None
                    
                jameiei = self.jsunpack_unpack(re_packed[0])
                
                # Extract M3U8 from unpacked code
                char_array = re.findall(r"\[(.+)\]", jameiei)
                if not char_array:
                    print("No character array found")
                    return None
                    
                m3u8 = "".join([chr(int(x)) for x in char_array[0].split(",")])
                print(f"Extracted M3U8: {m3u8}")
            
            return {
                "source_url": url,
                "m3u8_url": m3u8,
                "extracted_at": datetime.utcnow().isoformat(),
                "user_agent": self.user_agent
            }
            
        except requests.RequestException as e:
            print(f"Request error: {e}")
            return None
        except Exception as e:
            print(f"Extraction error: {e}")
            return None

def main():
    # Get URLs from environment variable or file
    urls_input = os.getenv('VOODC_URLS', '')
    
    if not urls_input:
        # Try reading from urls.txt if exists
        if os.path.exists('urls.txt'):
            with open('urls.txt', 'r') as f:
                urls_input = f.read()
    
    urls = [url.strip() for url in urls_input.split('\n') if url.strip()]
    
    if not urls:
        print("No URLs provided. Set VOODC_URLS environment variable or create urls.txt")
        return
    
    extractor = VoodcExtractor()
    results = []
    
    for url in urls:
        result = extractor.extract_link(url)
        if result:
            results.append(result)
    
    # Save results to JSON
    output_file = 'voodc_data.json'
    with open(output_file, 'w') as f:
        json.dump({
            "extracted_count": len(results),
            "last_updated": datetime.utcnow().isoformat(),
            "results": results
        }, f, indent=2)
    
    print(f"\nExtracted {len(results)} links")
    print(f"Results saved to {output_file}")

if __name__ == "__main__":
    main()
