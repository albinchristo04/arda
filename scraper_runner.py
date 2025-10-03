import json
import sys
import os
from datetime import datetime

# Mock Kodi modules before importing jetextractors
class MockAddon:
    def getAddonInfo(self, info):
        return "mock_value"

class MockXBMCAddon:
    def Addon(self, *args):
        return MockAddon()

class MockXBMC:
    def log(self, *args, **kwargs):
        pass
    
    def translatePath(self, path):
        return path

class MockXBMCGUI:
    pass

class MockXBMCVFS:
    pass

# Install mocks
sys.modules['xbmcaddon'] = MockXBMCAddon()
sys.modules['xbmc'] = MockXBMC()
sys.modules['xbmcgui'] = MockXBMCGUI()
sys.modules['xbmcvfs'] = MockXBMCVFS()

# Add the lib directory to the Python path
lib_path = os.path.join(os.path.dirname(__file__), 'repo', 'script.module.jetextractors', 'lib')
sys.path.insert(0, lib_path)

try:
    from jetextractors.plytvsites.stream720p import Stream720p
except ImportError as e:
    print(f"Import error: {e}")
    print(f"Current path: {os.getcwd()}")
    print(f"Lib path: {lib_path}")
    print(f"Lib path exists: {os.path.exists(lib_path)}")
    sys.exit(1)

def serialize_game(game):
    """Convert Game object to dictionary"""
    return {
        'title': game.title,
        'league': game.league,
        'icon': game.icon,
        'starttime': game.starttime.isoformat() if game.starttime else None,
        'links': [
            {
                'address': link.address,
                'name': link.name if hasattr(link, 'name') else None,
                'is_links': link.is_links if hasattr(link, 'is_links') else False
            }
            for link in game.links
        ]
    }

def main():
    try:
        scraper = Stream720p()
        print("Starting scrape...")
        
        games = scraper.get_games()
        print(f"Found {len(games)} games")
        
        # Convert games to JSON-serializable format
        games_data = [serialize_game(game) for game in games]
        
        # Prepare output data
        output = {
            'timestamp': datetime.utcnow().isoformat(),
            'total_games': len(games_data),
            'games': games_data
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
