import requests
import json
import re

# URLs
schedule_url = "https://dlhd.dad/schedule/schedule-generated.json"
daddy_url = "https://dlhd.dad/daddy.json"

def fetch_json(url):
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return []

def main():
    # Load JSONs
    schedule = fetch_json(schedule_url)
    daddy = fetch_json(daddy_url)

    print("=== Schedule Data ===")
    for item in schedule:
        print(item.get("title"), item.get("m3u8"), item.get("iframe"))

    print("\n=== Daddy Data ===")
    for item in daddy:
        print(item.get("title"), item.get("m3u8"), item.get("iframe"))

if __name__ == "__main__":
    main()
