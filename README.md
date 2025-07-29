# League of Legends Stats Integration

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)
[![hacs][hacsbadge]][hacs]

_Integration to monitor League of Legends player statistics in Home Assistant._

## ✨ Features

- **🎮 Real-time Game Tracking**: Know when you're in a game with honest status detection
- **📊 Match Statistics**: Track kills, deaths, assists, KDA, and win state from your latest matches
- **🏆 Rank Monitoring**: Current rank, LP, win rate, and ranked statistics  
- **🔥 Champion Information**: See which champion you last played
- **📈 Multiple Sensors**: 12 different sensors for comprehensive automation
- **⚡ Global API Key**: One API key for all summoners - easy 24h key rotation
- **⏱️ Configurable Polling**: 1-5 minute update intervals
- **🎯 Modern UI**: Easy setup through Home Assistant's integration UI

## 📦 Installation

### HACS (Recommended)

1. Ensure that [HACS](https://hacs.xyz/) is installed
2. Add this repository as a custom repository:
   - Go to HACS → Integrations → ⋮ → Custom repositories
   - Repository: `https://github.com/DariusTFox24/LeagueAssistant`
   - Category: Integration
   - Click "Add"
3. Find "League of Legends Stats" in HACS integrations
4. Install the integration
5. Restart Home Assistant

### Manual Installation

1. Download this repository (Code → Download ZIP)
2. Copy the `custom_components/riot_lol/` folder to your Home Assistant `custom_components/` directory
3. Restart Home Assistant

## ⚙️ Configuration

### 1. Get a Riot API Key

1. Go to the [Riot Developer Portal](https://developer.riotgames.com/)
2. Sign in with your Riot account
3. Create a new personal API key (expires every 24h) or production key
4. Copy the API key (format: `RGAPI-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`)

### 2. Initial Setup (v2.0.0+)

**Step 1: Configure API Key**
1. In Home Assistant, go to **Settings** > **Devices & Services**
2. Click **+ ADD INTEGRATION** and search for "League of Legends Stats"
3. **First setup**: Enter your Riot Games API key
4. This creates a global API key used by all summoners

**Step 2: Add Summoners**  
1. Click **+ ADD INTEGRATION** again and search for "League of Legends Stats"
2. **Add summoner**: Enter summoner details (no API key needed!)
   - **Game Name**: Your Riot ID game name (e.g., "PlayerName")  
   - **Tag Line**: Your tag line (e.g., "NA1", "EUW") - can be empty
   - **Region**: Platform region (e.g., "na1", "euw1", "kr")
   - **Update Interval**: How often to refresh (60-300 seconds)

3. **Repeat Step 2** for each summoner you want to track

### 3. Daily API Key Updates (Development Keys)

Development API keys expire every 24 hours. Easy renewal:

1. Go to **Settings** > **Devices & Services** > **League of Legends Stats**
2. Find the **"Riot Games API Key"** entry
3. Click **Configure** → Enter new API key → **Submit**
4. **All summoners automatically use the new key!**

## 📊 Sensors

The integration creates 12 comprehensive sensors for each summoner:

| Sensor | Description | Example Value |
|--------|-------------|---------------|
| `sensor.lol_{summoner}_game_state` | Honest game status detection | "In Game", "Recently Played", "Touching Grass" |
| `sensor.lol_{summoner}_kills` | Kills from latest match | `7` |
| `sensor.lol_{summoner}_deaths` | Deaths from latest match | `2` |
| `sensor.lol_{summoner}_assists` | Assists from latest match | `12` |
| `sensor.lol_{summoner}_kda_ratio` | Calculated KDA ratio | `9.5` |
| `sensor.lol_{summoner}_champion` | Last played champion | "Jinx" |
| `sensor.lol_{summoner}_rank` | Current ranked tier | "Gold II" |
| `sensor.lol_{summoner}_latest_match` | Latest match ID | "NA1_4567..." |
| `sensor.lol_{summoner}_level` | Account level | `156` |
| `sensor.lol_{summoner}_win_state` | Latest match result | "Victory", "Defeat" |
| `sensor.lol_{summoner}_win_rate` | Ranked win rate % | `67.8%` |

### Game State Detection

**Honest Status Based on API Reality:**
- **"In Game"** - Currently in an active League match
- **"Recently Played"** - Last match ended within 4 hours
- **"Touching Grass"** - Last match was 4+ hours ago

*Note: Riot API doesn't provide real online/offline status, so we use honest detection based on actual available data.*

## 🤖 Example Automations

### Game Start Notification

```yaml
automation:
  - alias: "LoL Game Started"
    trigger:
      - platform: state
        entity_id: sensor.lol_playername_game_state
        to: "In Game"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "League of Legends"
          message: "Game started as {{ states('sensor.lol_playername_champion') }}!"
```

### Victory Celebration

```yaml
automation:
  - alias: "LoL Victory Lights"
    trigger:
      - platform: state
        entity_id: sensor.lol_playername_win_state
        to: "Victory"
    action:
      - service: light.turn_on
        target:
          entity_id: light.living_room
        data:
          color_name: green
          brightness: 255
      - service: notify.mobile_app_your_phone
        data:
          title: "Victory!"
          message: "🏆 You won as {{ states('sensor.lol_playername_champion') }}! KDA: {{ states('sensor.lol_playername_kda_ratio') }}"
```

### Rank Change Alert

```yaml
automation:
  - alias: "LoL Rank Change"
    trigger:
      - platform: state
        entity_id: sensor.lol_playername_rank
    condition:
      - condition: template
        value_template: "{{ trigger.from_state.state != trigger.to_state.state }}"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "Rank Update!"
          message: "📈 Rank changed from {{ trigger.from_state.state }} to {{ trigger.to_state.state }}"
```

### Win Rate Tracker

```yaml
template:
  - sensor:
      - name: "LoL Performance Summary"
        state: >
          {{ states('sensor.lol_playername_rank') }} - {{ states('sensor.lol_playername_win_rate') }}% WR
        attributes:
          kda_display: "{{ states('sensor.lol_playername_kills') }}/{{ states('sensor.lol_playername_deaths') }}/{{ states('sensor.lol_playername_assists') }}"
          last_champion: "{{ states('sensor.lol_playername_champion') }}"
          last_result: "{{ states('sensor.lol_playername_win_state') }}"
```

## 🌍 Supported Regions

All official Riot Games regions are supported:
- **Americas**: na1, br1, la1, la2
- **Europe**: euw1, eun1, tr1, ru  
- **Asia**: kr, jp1
- **Southeast Asia**: oc1, ph2, sg2, th2, tw2, vn2

## ⚡ API Rate Limits & Performance

- **Respects Riot's rate limits** automatically
- **1-minute update intervals** for real-time tracking
- **Personal API keys**: 100 requests/2 minutes (perfect for personal use)
- **Production API keys**: Higher limits for multiple users
- **Intelligent caching** reduces API calls

## 🔧 Troubleshooting

### Common Issues

1. **"No API key configured" Error**
   - Set up the global API key first before adding summoners
   - Go to Integrations → Add Integration → League of Legends Stats → API Key Setup

2. **"Invalid API Key" Error**  
   - Personal API keys expire every 24 hours - update via Integration Options
   - Production keys don't expire

3. **"Riot ID not found" Error**
   - Verify Game Name and Tag Line are correct
   - Ensure you're using the correct region  
   - Tag line can be left empty for some accounts

4. **Sensors showing "Unknown" or "0"**
   - Play at least one match for data to appear
   - Check API key permissions
   - Verify region selection

### Migration from v1.x

**v2.0.0 requires full reconfiguration:**
1. **Remove** all existing League of Legends integrations
2. **Follow new setup process** (API key → summoners)
3. **Update automations** with new sensor names

### Debug Logging

Enable detailed logging in `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.riot_lol: debug
```

## 🎯 What's New in v2.0.0

- ✅ **Global API Key Management** - one key for all summoners
- ✅ **Runtime Key Updates** - no restart needed  
- ✅ **Win Rate Sensor** - track your ranked performance
- ✅ **Honest Game States** - realistic status detection
- ✅ **Victory/Defeat** terminology instead of Won/Lost
- ✅ **Enhanced Match History** tracking
- ✅ **12 Comprehensive Sensors** per summoner

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is under the MIT license.

---

[commits-shield]: https://img.shields.io/github/commit-activity/y/DariusTFox24/LeagueAssistant.svg?style=for-the-badge
[commits]: https://github.com/DariusTFox24/LeagueAssistant/commits/main
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[license-shield]: https://img.shields.io/github/license/DariusTFox24/LeagueAssistant.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/DariusTFox24/LeagueAssistant.svg?style=for-the-badge
[releases]: https://github.com/DariusTFox24/LeagueAssistant/releases
