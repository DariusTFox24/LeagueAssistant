# LeagueAssistant

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)
[![hacs][hacsbadge]][hacs]

A Home Assistant integration for tracking League of Legends player statistics and game status.

## Features

- Real-time game status detection using Riot's PUUID endpoints
- Track match statistics: kills, deaths, assists, KDA, win/loss
- Monitor current rank, LP, and win rate
- See champion info for current/last played match
- 11 sensors per summoner for comprehensive automation
- Global API key management - one key for all players
- Configurable update intervals (1-5 minutes)
- Support for all Riot Games regions

## Installation

### HACS (Recommended)

1. Install [HACS](https://hacs.xyz/)
2. Add custom repository:
   - HACS → Integrations → ⋮ → Custom repositories
   - Repository: `https://github.com/DariusTFox24/LeagueAssistant`
   - Category: Integration
3. Install "LeagueAssistant" from HACS
4. Restart Home Assistant

### Manual Installation

1. Download this repository
2. Copy `custom_components/lol_assist/` to your `custom_components/` directory
3. Restart Home Assistant

## Configuration

### Get a Riot API Key

1. Visit the [Riot Developer Portal](https://developer.riotgames.com/)
2. Sign in with your Riot account
3. Create a personal API key (expires every 24h)
4. Copy the key (format: `RGAPI-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`)

### Setup

**Step 1: Add API Key**
1. Settings → Devices & Services → Add Integration
2. Search for "LeagueAssistant"
3. Enter your Riot API key

**Step 2: Add Players**  
1. Add Integration → Search "LeagueAssistant" again
2. Enter player details:
   - **Game Name**: Riot ID (e.g., "PlayerName")  
   - **Tag Line**: Tag (e.g., "NA1") - optional
   - **Region**: Server region (e.g., "na1", "euw1")
   - **Update Interval**: Refresh rate (60-300 seconds)
3. Repeat for each player

### API Key Updates

Development keys expire daily. To update:
1. Settings → Devices & Services → LeagueAssistant
2. Find "Riot Games API Key" entry → Configure
3. Enter new key → Submit

## Sensors

Each player gets 11 sensors:

| Sensor | Description | Example |
|--------|-------------|---------|
| `sensor.lol_stats_playername_tag_game_state` | Current game status | "In Game", "Played Recently", "Touching Grass" |
| `sensor.lol_stats_playername_tag_kills` | Kills from latest match | `7` |
| `sensor.lol_stats_playername_tag_deaths` | Deaths from latest match | `2` |
| `sensor.lol_stats_playername_tag_assists` | Assists from latest match | `12` |
| `sensor.lol_stats_playername_tag_kda_ratio` | Calculated KDA | `9.5` |
| `sensor.lol_stats_playername_tag_champion` | Last/current champion | "Jinx" |
| `sensor.lol_stats_playername_tag_rank` | Current rank | "Gold II" |
| `sensor.lol_stats_playername_tag_latest_match` | Latest match ID | "NA1_4567..." |
| `sensor.lol_stats_playername_tag_level` | Account level | `156` |
| `sensor.lol_stats_playername_tag_win_state` | Latest match result | "Victory", "Defeat" |
| `sensor.lol_stats_playername_tag_win_rate` | Ranked win rate | `67.8%` |

### Game States

- **"In Game"** - Currently in a League match
- **"Played Recently"** - Last match ended within 4 hours  
- **"Touching Grass"** - No recent activity (4+ hours)

When "In Game", additional info includes current champion, game mode, and queue type.

## Automation Examples

### Game Started Notification

```yaml
automation:
  - alias: "League Game Started"
    trigger:
      platform: state
      entity_id: sensor.lol_stats_playername_tag_game_state
      to: "In Game"
    action:
      service: notify.mobile_app_your_phone
      data:
        title: "League of Legends"
        message: "Game started as {{ states('sensor.lol_stats_playername_tag_champion') }}!"
```

### Victory Lights

```yaml
automation:
  - alias: "Victory Celebration"
    trigger:
      platform: state
      entity_id: sensor.lol_stats_playername_tag_win_state
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
          message: "🏆 Won as {{ states('sensor.lol_stats_playername_tag_champion') }}! KDA: {{ states('sensor.lol_stats_playername_tag_kda_ratio') }}"
```

### Rank Change Alert

```yaml
automation:
  - alias: "Rank Change"
    trigger:
      platform: state
      entity_id: sensor.lol_stats_playername_tag_rank
    condition:
      condition: template
      value_template: "{{ trigger.from_state.state != trigger.to_state.state }}"
    action:
      service: notify.mobile_app_your_phone
      data:
        title: "Rank Update!"
        message: "📈 {{ trigger.from_state.state }} → {{ trigger.to_state.state }}"
```

### Performance Summary Template

```yaml
template:
  - sensor:
      - name: "League Performance"
        state: "{{ states('sensor.lol_stats_playername_tag_kills') }}/{{ states('sensor.lol_stats_playername_tag_deaths') }}/{{ states('sensor.lol_stats_playername_tag_assists') }}"
        attributes:
          kda_ratio: "{{ states('sensor.lol_stats_playername_tag_kda_ratio') }}"
          rank: "{{ states('sensor.lol_stats_playername_tag_rank') }}"
          win_rate: "{{ states('sensor.lol_stats_playername_tag_win_rate') }}"
          last_champion: "{{ states('sensor.lol_stats_playername_tag_champion') }}"
```

## Supported Regions

All Riot Games regions:
- **Americas**: na1, br1, la1, la2
- **Europe**: euw1, eun1, tr1, ru  
- **Asia**: kr, jp1
- **Southeast Asia**: oc1, ph2, sg2, th2, tw2, vn2

## ⚡ API Rate Limits & Performance

- **Modern PUUID Endpoints** - Uses latest Riot API recommendations
- **Respects Riot's rate limits** automatically
- **1-minute update intervals** for real-time tracking
- **Personal API keys**: 100 requests/2 minutes (perfect for personal use)
- **Production API keys**: Higher limits for multiple users
- **Intelligent caching** reduces API calls
- **Optimized current game detection** with fewer API requests

## Troubleshooting

### Common Issues

**"No API key configured"**
- Set up the API key first, then add players

**"Invalid API Key"**  
- Personal keys expire every 24 hours - update in Integration settings

**"Riot ID not found"**
- Check Game Name and Tag Line spelling
- Verify correct region selection

**Sensors showing "Unknown"**
- Play at least one match for data to appear
- Check API key is valid

### Debug Logging

```yaml
# configuration.yaml
logger:
  logs:
    custom_components.lol_assist: debug
```

## What's New in v3.0.0

- Domain changed from `riot_lol` to `lol_assist` for legal safety
- Entity IDs remain as `lol_stats_*` for automation compatibility  
- Updated branding to "LeagueAssistant"
- Improved legal compliance documentation

## Contributing

Pull requests welcome!

## License

MIT License

---

[commits-shield]: https://img.shields.io/github/commit-activity/y/DariusTFox24/LeagueAssistant.svg?style=for-the-badge
[commits]: https://github.com/DariusTFox24/LeagueAssistant/commits/main
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[license-shield]: https://img.shields.io/github/license/DariusTFox24/LeagueAssistant.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/DariusTFox24/LeagueAssistant.svg?style=for-the-badge
[releases]: https://github.com/DariusTFox24/LeagueAssistant/releases
