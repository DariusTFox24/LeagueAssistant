# League of Legends Match History Integration

## New Features Added

### 📈 Match History Sensor
- **Entity**: `sensor.lol_stats_[your_riot_id]_match_history`
- **Description**: Tracks your last 10 match IDs
- **Value**: Number of matches in history (0-10)
- **Attributes**:
  - `match_ids`: Array of the last 10 match IDs
  - `latest_match_id`: ID of your most recent match
  - `total_matches`: Total number of matches in history

### 🏆 Latest Match Sensor
- **Entity**: `sensor.lol_stats_[your_riot_id]_latest_match`
- **Description**: Detailed statistics from your most recent completed match
- **Value**: "Victory", "Defeat", or "No matches"
- **Attributes**:
  - `match_id`: Match identifier
  - `champion`: Champion played
  - `champion_level`: Final champion level
  - `kills`, `deaths`, `assists`: KDA stats
  - `kda`: Calculated KDA ratio
  - `game_mode`: Game mode (e.g., "CLASSIC", "ARAM")
  - `duration`: Formatted game duration (MM:SS)
  - `total_damage_dealt`: Damage to champions
  - `total_damage_taken`: Damage received
  - `gold_earned`: Total gold earned
  - `cs_total`: Creep score (minions + monsters)
  - `vision_score`: Vision score
  - `items`: Array of item IDs
  - `win`: Boolean win/loss

## API Endpoints Used

### Match History
```
GET https://europe.api.riotgames.com/lol/match/v5/matches/by-puuid/{PUUID}/ids?start=0&count=10
```
Returns array of match IDs:
```json
[
    "EUN1_3799067374",
    "EUN1_3797976125",
    "EUN1_3797951319",
    ...
]
```

### Match Details
```
GET https://europe.api.riotgames.com/lol/match/v5/matches/{matchId}
```
Returns comprehensive match data including all participants and detailed statistics.

## Automation Examples

### 🚨 New Match Trigger
```yaml
automation:
  - alias: "LoL New Match Notification"
    trigger:
      - platform: state
        entity_id: sensor.lol_stats_yourname_euw_latest_match
    condition:
      - condition: template
        value_template: "{{ trigger.to_state.state != trigger.from_state.state }}"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "LoL Match Complete!"
          message: >
            {{ trigger.to_state.state }} as {{ trigger.to_state.attributes.champion }}
            KDA: {{ trigger.to_state.attributes.kills }}/{{ trigger.to_state.attributes.deaths }}/{{ trigger.to_state.attributes.assists }}
```

### 📊 Victory Celebration
```yaml
automation:
  - alias: "LoL Victory Lights"
    trigger:
      - platform: state
        entity_id: sensor.lol_stats_yourname_euw_latest_match
        to: "Victory"
    action:
      - service: light.turn_on
        target:
          entity_id: light.desk_lamp
        data:
          color_name: green
          brightness: 255
      - delay: '00:00:05'
      - service: light.turn_off
        target:
          entity_id: light.desk_lamp
```

### 📈 Match Statistics Dashboard
```yaml
# Add to your dashboard
type: entities
entities:
  - entity: sensor.lol_stats_yourname_euw_latest_match
    name: "Latest Match"
  - entity: sensor.lol_stats_yourname_euw_match_history
    name: "Match History"
  - entity: sensor.lol_stats_yourname_euw_rank
    name: "Current Rank"
title: "League of Legends Stats"
```

## Update Frequency

- **Match data**: Checked every 1 minute
- **Smart detection**: Only fetches new match details when a new match ID is detected
- **Rate limiting**: Respects Riot API rate limits with proper error handling

## Troubleshooting

### No Match Data
1. Ensure you've played at least one match recently
2. Check the logs for API errors
3. Verify your API key is valid

### Missing Latest Match
1. The sensor only updates when a new match is completed
2. Check that the match history sensor shows match IDs
3. Look for coordinator warnings in the logs

### Automation Not Triggering
1. Verify the entity name matches your configuration
2. Ensure the state actually changes (Victory/Defeat)
3. Check automation traces in Home Assistant

## Technical Notes

- Uses PUUID-based endpoints for reliability
- Caches match data to avoid redundant API calls
- Gracefully handles API rate limits and errors
- Stores comprehensive match data for advanced use cases
