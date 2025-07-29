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

## Sensors

The integration creates the following sensors:

| Sensor | Description |
|--------|-------------|
| `sensor.lol_stats_game_state` | Current game state (In Game, Online, Offline, etc.) |
| `sensor.lol_stats_kills` | Kills from current/latest match |
| `sensor.lol_stats_deaths` | Deaths from current/latest match |
| `sensor.lol_stats_assists` | Assists from current/latest match |
| `sensor.lol_stats_kda_ratio` | Calculated KDA ratio |
| `sensor.lol_stats_champion` | Current/last played champion |
| `sensor.lol_stats_rank` | Current ranked tier and division |

## Example Automations

### Game Start Notification

```yaml
automation:
  - alias: "LoL Game Started"
    trigger:
      - platform: state
        entity_id: sensor.lol_stats_game_state
        to: "In Game"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "League of Legends"
          message: "Game started as {{ states.sensor.lol_stats_champion.state }}!"
```

### Victory Celebration

```yaml
automation:
  - alias: "LoL Victory Lights"
    trigger:
      - platform: state
        entity_id: sensor.lol_stats_game_state
        from: "In Game"
        to: "Online"
    condition:
      - condition: template
        value_template: "{{ trigger.to_state.attributes.win == true }}"
    action:
      - service: light.turn_on
        target:
          entity_id: light.living_room
        data:
          color_name: green
          brightness: 255
```

### KDA Display Template

```yaml
template:
  - sensor:
      - name: "LoL KDA Display"
        state: >
          {{ states('sensor.lol_stats_kills') }}/{{ states('sensor.lol_stats_deaths') }}/{{ states('sensor.lol_stats_assists') }}
        attributes:
          kda_ratio: "{{ states('sensor.lol_stats_kda_ratio') }}"
```

## Supported Regions

All official Riot Games regions are supported:
- **Americas**: na1, br1, la1, la2
- **Europe**: euw1, eun1, tr1, ru
- **Asia**: kr, jp1
- **Southeast Asia**: oc1, ph2, sg2, th2, tw2, vn2

## API Rate Limits

This integration respects Riot's API rate limits:
- Personal API keys: 100 requests every 2 minutes
- Production API keys: Higher limits available

The integration automatically handles rate limiting and will back off when limits are reached.

## Troubleshooting

### Common Issues

1. **"Invalid API Key" Error**
   - Ensure your API key is correct and hasn't expired
   - Personal API keys expire every 24 hours

2. **"Riot ID not found" Error**
   - Verify your Game Name and Tag Line are correct
   - Make sure you're using the correct region

3. **No Data Updates**
   - Check that you've played a recent match
   - Verify your API key permissions

### Debug Logging

To enable debug logging, add this to your `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.riot_lol: debug
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is under the MIT license.

---

[commits-shield]: https://img.shields.io/github/commit-activity/y/your-username/league-assistant.svg?style=for-the-badge
[commits]: https://github.com/your-username/league-assistant/commits/main
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[license-shield]: https://img.shields.io/github/license/your-username/league-assistant.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/your-username/league-assistant.svg?style=for-the-badge
[releases]: https://github.com/your-username/league-assistant/releases
