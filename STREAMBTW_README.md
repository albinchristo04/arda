# StreamBTW Sports Data

🏆 Automated extraction of sports streaming events from StreamBTW

## 📊 Statistics

- **Last Updated**: 2025-10-04T08:02:26.645432
- **Total Events**: 37
- **Sports Categories**: 11

## 🏅 Available Sports

- 🥊 **BOXING**: 1 events
- 🎯 **BUNDESLIGA**: 5 events
- 🎯 **EFL**: 7 events
- 🎯 **F1**: 1 events
- 🎯 **LALIGA**: 4 events
- 🎯 **LIGA PORTUGAL**: 4 events
- 🎯 **LIGUE 1**: 3 events
- 🎯 **NBA**: 3 events
- 🎯 **PREMIER LEAGUE**: 4 events
- 🎯 **SERIE A**: 4 events
- 🎯 **UFC**: 1 events


## 📁 Files

- `streambtw_data.json` - Complete data in JSON format
- `streambtw_data.html` - Interactive HTML view

## 🔄 Update Frequency

This data is automatically updated every 3 hours to catch live sports events.

## 📖 Usage

### View the data
```bash
# View JSON
cat streambtw_data.json | jq '.'

# Get events by sport
cat streambtw_data.json | jq '.by_sport.FOOTBALL'

# Count total events
cat streambtw_data.json | jq '.total_items'
```

### Open HTML view
Open `streambtw_data.html` in your browser for an interactive view.

---

*Generated automatically by GitHub Actions*
