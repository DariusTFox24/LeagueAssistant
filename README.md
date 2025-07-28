# League of Legends Stats Integration

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)
[![hacs][hacsbadge]][hacs]

_Integration to monitor League of Legends player statistics in Home Assistant._

## Features

- **Real-time Game Tracking**: Know when you're in a game, in queue, or online
- **Match Statistics**: Automatically track kills, deaths, assists, and KDA from your latest matches
- **Rank Monitoring**: Keep track of your current rank, LP, and win/loss record
- **Champion Information**: See which champion you're currently playing
- **Multiple Sensors**: Separate sensors for different statistics for easy automation
- **Configurable Polling**: Adjust how often data is refreshed (1 minute to 1 hour)
- **Modern UI Configuration**: Easy setup through Home Assistant's integration UI

## Installation

### HACS (Recommended)

1. Ensure that [HACS](https://hacs.xyz/) is installed
2. Search for "League of Legends Stats" in the integrations section
3. Install the integration
4. Restart Home Assistant

### Manual Installation

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`)
2. If you do not have a `custom_components` directory (folder) there, you need to create it
3. In the `custom_components` directory (folder) create a new folder called `riot_lol`
4. Download _all_ the files from the `custom_components/riot_lol/` directory (folder) in this repository
5. Place the files you downloaded in the new directory (folder) you created
6. Restart Home Assistant

## Configuration

### 1. Get a Riot API Key

1. Go to the [Riot Developer Portal](https://developer.riotgames.com/)
2. Sign in with your Riot account
3. Create a new personal API key
4. Copy the API key (it will look like `RGAPI-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`)

### 2. Set Up the Integration

1. In Home Assistant, go to **Configuration** > **Integrations**
2. Click the **+** button to add a new integration
3. Search for "League of Legends Stats"
4. Enter your configuration:
   - **API Key**: Your Riot API key from step 1
   - **Game Name**: Your Riot ID game name (e.g., "PlayerName")
   - **Tag Line**: Your Riot ID tag line (e.g., "NA1") - Optional
   - **Region**: Your platform region (e.g., "na1", "euw1", "kr")

### 3. Configure Options (Optional)

After setup, you can configure additional options:
- **Scan Interval**: How often to check for updates (60-3600 seconds, default: 300)

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
