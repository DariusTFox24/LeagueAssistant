"""Riot LoL sensor platform."""
import logging
from datetime import timedelta

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN
from .coordinator import RiotLoLDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Riot LoL sensors based on a config entry."""
    coordinator: RiotLoLDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    # Create different sensors for various stats
    sensors = [
        RiotLoLGameStateSensor(coordinator, config_entry),
        RiotLoLKillsSensor(coordinator, config_entry),
        RiotLoLDeathsSensor(coordinator, config_entry),
        RiotLoLAssistsSensor(coordinator, config_entry),
        RiotLoLKDASensor(coordinator, config_entry),
        RiotLoLChampionSensor(coordinator, config_entry),
        RiotLoLRankSensor(coordinator, config_entry),
        RiotLoLLatestMatchSensor(coordinator, config_entry),
        RiotLoLLevelSensor(coordinator, config_entry),
        RiotLoLWinStateSensor(coordinator, config_entry),
        RiotLoLWinRateSensor(coordinator, config_entry),
    ]
    
    async_add_entities(sensors, True)


class RiotLoLBaseSensor(CoordinatorEntity, SensorEntity):
    """Base class for Riot LoL sensors."""

    def __init__(self, coordinator: RiotLoLDataUpdateCoordinator, config_entry: ConfigEntry, sensor_type: str):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._sensor_type = sensor_type
        self._attr_has_entity_name = True
        
        # Get riot_id from config entry data
        riot_id = config_entry.data.get("riot_id", "Unknown Player")
        region = config_entry.data.get("region", "unknown")
        
        self._attr_unique_id = f"{config_entry.entry_id}_{sensor_type}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": f"LoL Stats - {riot_id}",
            "manufacturer": "Riot Games",
            "model": "League of Legends",
            "sw_version": region.upper(),
        }

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success and self.coordinator.data is not None


class RiotLoLGameStateSensor(RiotLoLBaseSensor):
    """Sensor for current game state."""

    def __init__(self, coordinator: RiotLoLDataUpdateCoordinator, config_entry: ConfigEntry):
        """Initialize the game state sensor."""
        super().__init__(coordinator, config_entry, "game_state")
        self._attr_name = "Game State"
        self._attr_icon = "mdi:gamepad-variant"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return "Unknown"
        return self.coordinator.data.get("state", "Unknown")

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        if not self.coordinator.data:
            return {}
        
        attributes = {
            "last_updated": self.coordinator.data.get("last_updated"),
            "game_mode": self.coordinator.data.get("game_mode"),
            "queue_type": self.coordinator.data.get("queue_type"),
            "match_id": self.coordinator.data.get("match_id"),
        }
        
        # Add champion info if in game
        state = self.coordinator.data.get("state")
        if state == "In Game":
            attributes.update({
                "champion": self.coordinator.data.get("champion"),
                "champion_id": self.coordinator.data.get("champion_id"),
                "queue_id": self.coordinator.data.get("queue_id"),
                "map_name": self.coordinator.data.get("map_name"),
                "map_id": self.coordinator.data.get("map_id"),
                "game_type": self.coordinator.data.get("game_type"),
                "game_start_time": self.coordinator.data.get("game_start_time_formatted"),  # Human readable
                "game_duration": self.coordinator.data.get("game_duration"),  # Human readable
                "game_start_time_raw": self.coordinator.data.get("game_start_time"),  # Raw epoch for automations
                "game_length_raw": self.coordinator.data.get("game_length"),  # Raw seconds for automations
            })
            
        return attributes


class RiotLoLKillsSensor(RiotLoLBaseSensor):
    """Sensor for kills in current/last game."""

    def __init__(self, coordinator: RiotLoLDataUpdateCoordinator, config_entry: ConfigEntry):
        """Initialize the kills sensor."""
        super().__init__(coordinator, config_entry, "kills")
        self._attr_name = "Kills"
        self._attr_icon = "mdi:sword"
        self._attr_native_unit_of_measurement = "kills"

    @property
    def native_value(self):
        """Return the kills count from latest match."""
        if not self.coordinator.data:
            return 0
        
        # Use latest match data primarily, fallback to current game data
        latest_kills = self.coordinator.data.get("latest_kills")
        if latest_kills is not None:
            return latest_kills
        
        return self.coordinator.data.get("kills", 0)


class RiotLoLDeathsSensor(RiotLoLBaseSensor):
    """Sensor for deaths in current/last game."""

    def __init__(self, coordinator: RiotLoLDataUpdateCoordinator, config_entry: ConfigEntry):
        """Initialize the deaths sensor."""
        super().__init__(coordinator, config_entry, "deaths")
        self._attr_name = "Deaths"
        self._attr_icon = "mdi:skull"
        self._attr_native_unit_of_measurement = "deaths"

    @property
    def native_value(self):
        """Return the deaths count from latest match."""
        if not self.coordinator.data:
            return 0
        
        # Use latest match data primarily, fallback to current game data
        latest_deaths = self.coordinator.data.get("latest_deaths")
        if latest_deaths is not None:
            return latest_deaths
        
        return self.coordinator.data.get("deaths", 0)


class RiotLoLAssistsSensor(RiotLoLBaseSensor):
    """Sensor for assists in current/last game."""

    def __init__(self, coordinator: RiotLoLDataUpdateCoordinator, config_entry: ConfigEntry):
        """Initialize the assists sensor."""
        super().__init__(coordinator, config_entry, "assists")
        self._attr_name = "Assists"
        self._attr_icon = "mdi:hand-heart"
        self._attr_native_unit_of_measurement = "assists"

    @property
    def native_value(self):
        """Return the assists count from latest match."""
        if not self.coordinator.data:
            return 0
        
        # Use latest match data primarily, fallback to current game data
        latest_assists = self.coordinator.data.get("latest_assists")
        if latest_assists is not None:
            return latest_assists
        
        return self.coordinator.data.get("assists", 0)


class RiotLoLKDASensor(RiotLoLBaseSensor):
    """Sensor for KDA ratio."""

    def __init__(self, coordinator: RiotLoLDataUpdateCoordinator, config_entry: ConfigEntry):
        """Initialize the KDA sensor."""
        super().__init__(coordinator, config_entry, "kda")
        self._attr_name = "KDA Ratio"
        self._attr_icon = "mdi:calculator"

    @property
    def native_value(self):
        """Return the KDA ratio from latest match."""
        if not self.coordinator.data:
            return 0.0
        
        # Use latest match data primarily, fallback to current game data
        latest_kda = self.coordinator.data.get("latest_kda")
        if latest_kda is not None:
            return latest_kda
        
        # Use pre-calculated KDA from coordinator, fallback to manual calculation
        kda = self.coordinator.data.get("kda")
        if kda is not None:
            return kda
            
        # Fallback calculation if coordinator doesn't provide KDA
        kills = self.coordinator.data.get("kills", 0)
        deaths = self.coordinator.data.get("deaths", 0)
        assists = self.coordinator.data.get("assists", 0)
        
        if deaths == 0:
            return kills + assists  # Perfect KDA
        
        return round((kills + assists) / deaths, 2)


class RiotLoLChampionSensor(RiotLoLBaseSensor):
    """Sensor for current champion."""

    def __init__(self, coordinator: RiotLoLDataUpdateCoordinator, config_entry: ConfigEntry):
        """Initialize the champion sensor."""
        super().__init__(coordinator, config_entry, "champion")
        self._attr_name = "Champion"
        self._attr_icon = "mdi:account"

    @property
    def native_value(self):
        """Return the current or latest match champion."""
        if not self.coordinator.data:
            return "Unknown"
        
        # Use latest match data primarily, fallback to current game data
        latest_champion = self.coordinator.data.get("latest_champion")
        if latest_champion:
            return latest_champion
        
        return self.coordinator.data.get("champion", "Unknown")

    @property
    def extra_state_attributes(self):
        """Return additional champion attributes."""
        if not self.coordinator.data:
            return {}
        
        return {
            "champion_level": self.coordinator.data.get("champion_level"),
            "champion_mastery": self.coordinator.data.get("champion_mastery"),
        }


class RiotLoLRankSensor(RiotLoLBaseSensor):
    """Sensor for current rank."""

    def __init__(self, coordinator: RiotLoLDataUpdateCoordinator, config_entry: ConfigEntry):
        """Initialize the rank sensor."""
        super().__init__(coordinator, config_entry, "rank")
        self._attr_name = "Rank"
        self._attr_icon = "mdi:trophy"

    @property
    def native_value(self):
        """Return the current rank."""
        if not self.coordinator.data:
            return "Unranked"
        return self.coordinator.data.get("rank", "Unranked")

    @property
    def extra_state_attributes(self):
        """Return additional rank attributes."""
        if not self.coordinator.data:
            return {}
        
        return {
            "tier": self.coordinator.data.get("tier"),
            "division": self.coordinator.data.get("division"),
            "lp": self.coordinator.data.get("lp"),
            "wins": self.coordinator.data.get("wins"),
            "losses": self.coordinator.data.get("losses"),
            "win_rate": self.coordinator.data.get("win_rate"),
        }


class RiotLoLLatestMatchSensor(RiotLoLBaseSensor):
    """Sensor for latest match ID."""

    def __init__(self, coordinator: RiotLoLDataUpdateCoordinator, config_entry: ConfigEntry):
        """Initialize the latest match sensor."""
        super().__init__(coordinator, config_entry, "latest_match")
        self._attr_name = "Latest Match ID"
        self._attr_icon = "mdi:identifier"

    @property
    def native_value(self):
        """Return the latest match ID."""
        if not self.coordinator.data:
            return "No matches"
        
        latest_match_id = self.coordinator.data.get("latest_match_id")
        if latest_match_id:
            return latest_match_id
        
        return "No matches"

    @property
    def extra_state_attributes(self):
        """Return basic match information."""
        if not self.coordinator.data:
            return {}
        
        latest_match_data = self.coordinator.data.get("latest_match_data")
        if not latest_match_data:
            return {}
        
        # Format game duration
        duration_seconds = latest_match_data.get("game_duration", 0)
        if duration_seconds > 0:
            minutes = duration_seconds // 60
            seconds = duration_seconds % 60
            duration_formatted = f"{minutes}:{seconds:02d}"
        else:
            duration_formatted = "Unknown"
        
        return {
            "result": "Victory" if latest_match_data.get("win") else "Defeat" if latest_match_data.get("win") is False else "Unknown",
            "game_mode": latest_match_data.get("game_mode"),
            "duration": duration_formatted,
            "champion": latest_match_data.get("champion"),
        }


class RiotLoLLevelSensor(RiotLoLBaseSensor):
    """Sensor for summoner account level."""

    def __init__(self, coordinator: RiotLoLDataUpdateCoordinator, config_entry: ConfigEntry):
        """Initialize the level sensor."""
        super().__init__(coordinator, config_entry, "level")
        self._attr_name = "Account Level"
        self._attr_icon = "mdi:counter"
        self._attr_native_unit_of_measurement = "level"

    @property
    def native_value(self):
        """Return the summoner account level."""
        if not self.coordinator.data:
            return 0
        return self.coordinator.data.get("summoner_level", 0)


class RiotLoLWinStateSensor(RiotLoLBaseSensor):
    """Sensor for latest match win state."""

    def __init__(self, coordinator: RiotLoLDataUpdateCoordinator, config_entry: ConfigEntry):
        """Initialize the win state sensor."""
        super().__init__(coordinator, config_entry, "win_state")
        self._attr_name = "Latest Match Result"
        self._attr_icon = "mdi:trophy-variant"

    @property
    def native_value(self):
        """Return the latest match result (Victory/Defeat/Unknown)."""
        if not self.coordinator.data:
            return "Unknown"
        
        # Use latest match data
        latest_win = self.coordinator.data.get("latest_win")
        if latest_win is True:
            return "Victory"
        elif latest_win is False:
            return "Defeat"
        else:
            return "Unknown"

    @property
    def extra_state_attributes(self):
        """Return additional match result information."""
        if not self.coordinator.data:
            return {}
        
        latest_match_data = self.coordinator.data.get("latest_match_data")
        if not latest_match_data:
            return {}
        
        return {
            "match_id": latest_match_data.get("match_id"),
            "champion": latest_match_data.get("champion"),
            "game_mode": latest_match_data.get("game_mode"),
            "win": latest_match_data.get("win"),
        }


class RiotLoLWinRateSensor(RiotLoLBaseSensor):
    """Sensor for current ranked win rate percentage."""

    def __init__(self, coordinator: RiotLoLDataUpdateCoordinator, config_entry: ConfigEntry):
        """Initialize the win rate sensor."""
        super().__init__(coordinator, config_entry, "win_rate")
        self._attr_name = "Ranked Win Rate"
        self._attr_icon = "mdi:percent"
        self._attr_unit_of_measurement = "%"
        self._attr_state_class = "measurement"

    @property
    def native_value(self):
        """Return the current ranked win rate percentage."""
        if not self.coordinator.data:
            return None
        
        # Get win rate from ranked data
        win_rate = self.coordinator.data.get("win_rate")
        if win_rate is not None:
            return round(win_rate, 1)
        else:
            return None

    @property
    def extra_state_attributes(self):
        """Return additional win rate information."""
        if not self.coordinator.data:
            return {}
        
        wins = self.coordinator.data.get("wins", 0)
        losses = self.coordinator.data.get("losses", 0)
        total_games = wins + losses
        
        return {
            "wins": wins,
            "losses": losses,
            "total_games": total_games,
            "rank": self.coordinator.data.get("rank", "Unranked"),
        }
