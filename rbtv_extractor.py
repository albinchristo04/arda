import base64
import requests
import uuid
import os
import time
import json
from itertools import chain
from pyamf import remoting, AMF3
from pyamf.flex import messaging

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
    user_agent = "Dalvik/2.1.0 (Linux; U; Android 9; AFTKA Build/PS7255)"
    
    # Additional domains
    domains = [
        "rbtv.com",
        "www.fctv33.buzz",
        "genegc02.ya8z6nutsz3jhbtmail.shop"
    ]

    def __init__(self):
        self.name = "RBTV"

    def extract_all_data(self):
        """Main method to extract all data"""
        self.__fetch_config()
        self.__register_user()
        self.__fetch_videos()
        self.json_config["data_age"] = time.time()
        self.json_config["extraction_date"] = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
        return self.json_config

    def __fetch_config(self):
        """Fetch configuration from Backendless API"""
        data = {
            "clientId": None,
            "destination": "GenericDestination",
            "correlationId": None,
            "source": "com.backendless.services.persistence.PersistenceService",
            "operation": "first",
            "messageRefType": None,
            "headers": {"application-type": "ANDROID", "api-version": "1.0"},
            "timestamp": 0,
            "body": ["AppConfigHotel"],
            "timeToLive": 0,
            "messageId": None,
        }
        req = remoting.Request(target="null", body=[messaging.RemotingMessage(**data)])
        ev = remoting.Envelope(AMF3)
        ev["null"] = req
        
        resp = requests.post(
            self.config_url,
            data=remoting.encode(ev).getvalue(),
            headers={"Content-Type": "application/x-amf", "User-Agent": self.user_agent},
            timeout=10,
            verify=False,
        )
        resp.raise_for_status()
        
        amf_data = remoting.decode(resp.content).bodies[0][1].body.body
        self.json_config["api_url"] = self.__decode_value(amf_data["YmFzZXVybG5ld3gw"])
        self.json_config["api_referer"] = self.__decode_value(amf_data["SXNpc2VrZWxvX3Nlc2lzdGltdV95ZXppbm9tYm9sbzAw"])
        self.json_config["api_authorization"] = self.__decode_value(amf_data["amFnX3Ryb3JfYXR0X2Vu"])
        self.json_config["token_url_21"] = self.__decode_value(amf_data["Y2FsYWFtb19pa3Mw"])
        self.json_config["token_auth_21"] = self.__decode_value(amf_data["WXJfd3lmX3luX2JhaXMw"])
        self.json_config["token_url_38"] = self.__decode_value(amf_data["YmVsZ2lfMzgw"])
        self.json_config["token_auth_38"] = self.__decode_value(amf_data["Z2Vsb29mc2JyaWVm"])
        self.json_config["token_url_48"] = self.__decode_value(amf_data["Ym9ya3lsd3VyXzQ4"])
        self.json_config["token_auth_48"] = self.__decode_value(amf_data["dGVydHRleWFj"])
        self.json_config["mod_value"] = self.__decode_value(amf_data["TW9vbl9oaWsx"])
        self.json_config["domains"] = self.domains

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
        user_id = self.__api_request(self.json_config["api_url"] + "adduserinfo.nettv/", data).get("user_id")
        self.json_config["user"] = {"user_id": user_id, "check": 41}

    def __fetch_videos(self):
        """Fetch all videos, categories, and countries"""
        data = {
            "check": self.json_config["user"]["check"],
            "user_id": self.json_config["user"]["user_id"],
            "version": "41",
            "hash_id": self.enc_aes_cbc_single(
                f'{self.json_config["user"]["user_id"]}_wdufherfbweicerwf',
                f'{self.json_config["user"]["user_id"]}cefrecdce'.encode("utf-8")[:16],
                f'{self.json_config["user"]["user_id"]}cwefervwv'.encode("utf-8")[:16],
            )
        }
        res = self.__api_request(self.json_config["api_url"] + "redbox.tv/", data)
        
        categories = [{"category_id": item["cat_id"], "title": item["cat_name"]} for item in res["categories_list"]]
        countries = [{"country_id": item["country_id"], "title": item["country_name"]} for item in res["countries_list"]]
        videos = [{
            "video_id": int(self.__decode_value2(item["rY19pZA=="])),
            "category": item["cat_id"],
            "country": item["country_id"],
            "title": self.__decode_value2(item["ZY19uYW1l"]),
            "logo_url": self.__decode_value(item["abG9nb191cmw="]),
            "streams": [{
                "stream_id": self.__decode_value2(stream["cc3RyZWFtX2lk"]),
                "video_id": self.__decode_value2(item["rY19pZA=="]),
                "token": int(self.__decode_value2(stream["AdG9rZW4="])),
                "stream_url": self.__decode_value(stream["Bc3RyZWFtX3VybA=="]),
            } for stream in item["Qc3RyZWFtX2xpc3Q="]]
        } for item in res["eY2hhbm5lbHNfbGlzdA=="]]
        
        self.json_config["categories"] = categories
        self.json_config["countries"] = countries
        self.json_config["videos"] = videos
        self.json_config["total_videos"] = len(videos)
        self.json_config["total_categories"] = len(categories)
        self.json_config["total_countries"] = len(countries)

    def __api_request(self, url, data):
        """Make API request with headers"""
        headers = {
            "Referer": self.json_config["api_referer"],
            "Authorization": self.json_config["api_authorization"],
            "User-Agent": self.user_agent
        }
        r = requests.post(url, headers=headers, data=data, timeout=10, verify=False)
        r.raise_for_status()
        return r.json()

    def __decode_value(self, v):
        """Decode base64 value (skip first character)"""
        return base64.b64decode(v[1:]).decode("utf-8")

    def __decode_value2(self, v):
        """Decode base64 value (skip last character)"""
        return base64.b64decode(v[:-1]).decode("utf-8")

    def enc_aes_cbc_single(self, msg, key, iv):
        """Encrypt message using AES CBC"""
        cipher = AES.new(key, AES.MODE_CBC, iv=iv)
        return base64.b64encode(cipher.encrypt(pad(msg.encode("utf-8"), 16))).decode("utf-8")


def main():
    """Main execution function"""
    print("Starting RBTV data extraction...")
    
    extractor = RBTVExtractor()
    
    try:
        data = extractor.extract_all_data()
        
        # Create data directory if it doesn't exist
        os.makedirs("data", exist_ok=True)
        
        # Save full data
        with open("data/rbtv_data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # Create a summary file
        summary = {
            "extraction_date": data["extraction_date"],
            "total_videos": data["total_videos"],
            "total_categories": data["total_categories"],
            "total_countries": data["total_countries"],
            "domains": data["domains"]
        }
        
        with open("data/summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
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
        
        print(f"✓ Extraction completed successfully!")
        print(f"✓ Total videos: {data['total_videos']}")
        print(f"✓ Total categories: {data['total_categories']}")
        print(f"✓ Total countries: {data['total_countries']}")
        print(f"✓ Data saved to data/ directory")
        
    except Exception as e:
        print(f"✗ Error during extraction: {str(e)}")
        raise


if __name__ == "__main__":
    main()
