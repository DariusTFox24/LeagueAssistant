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
        RiotLoLMatchHistorySensor(coordinator, config_entry),
        RiotLoLLatestMatchSensor(coordinator, config_entry),
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
        
        return {
            "last_updated": self.coordinator.data.get("last_updated"),
            "game_mode": self.coordinator.data.get("game_mode"),
            "queue_type": self.coordinator.data.get("queue_type"),
            "match_id": self.coordinator.data.get("match_id"),
        }


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
        """Return the kills count."""
        if not self.coordinator.data:
            return 0
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
        """Return the deaths count."""
        if not self.coordinator.data:
            return 0
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
        """Return the assists count."""
        if not self.coordinator.data:
            return 0
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
        """Return the KDA ratio."""
        if not self.coordinator.data:
            return 0.0
        
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
        """Return the current champion."""
        if not self.coordinator.data:
            return "Unknown"
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


class RiotLoLMatchHistorySensor(RiotLoLBaseSensor):
    """Sensor for match history (last 10 match IDs)."""

    def __init__(self, coordinator: RiotLoLDataUpdateCoordinator, config_entry: ConfigEntry):
        """Initialize the match history sensor."""
        super().__init__(coordinator, config_entry, "match_history")
        self._attr_name = "Match History"
        self._attr_icon = "mdi:history"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self):
        """Return the number of matches in history."""
        match_history = self.coordinator.match_history
        if not match_history:
            return 0
        return len(match_history)

    @property
    def extra_state_attributes(self):
        """Return match history details."""
        match_history = self.coordinator.match_history
        if not match_history:
            return {"match_ids": []}
        
        return {
            "match_ids": match_history,
            "latest_match_id": match_history[0] if match_history else None,
            "total_matches": len(match_history),
        }


class RiotLoLLatestMatchSensor(RiotLoLBaseSensor):
    """Sensor for latest match detailed stats."""

    def __init__(self, coordinator: RiotLoLDataUpdateCoordinator, config_entry: ConfigEntry):
        """Initialize the latest match sensor."""
        super().__init__(coordinator, config_entry, "latest_match")
        self._attr_name = "Latest Match"
        self._attr_icon = "mdi:trophy"

    @property
    def native_value(self):
        """Return the match result (Win/Loss/Unknown)."""
        latest_match = self.coordinator.latest_match_data
        if not latest_match:
            return "No matches"
        
        win = latest_match.get("win")
        if win is True:
            return "Victory"
        elif win is False:
            return "Defeat"
        else:
            return "Unknown"

    @property
    def extra_state_attributes(self):
        """Return comprehensive latest match data."""
        latest_match = self.coordinator.latest_match_data
        if not latest_match:
            return {}
        
        # Format game duration
        duration_seconds = latest_match.get("game_duration", 0)
        if duration_seconds > 0:
            minutes = duration_seconds // 60
            seconds = duration_seconds % 60
            duration_formatted = f"{minutes}:{seconds:02d}"
        else:
            duration_formatted = "Unknown"
        
        # Format timestamps
        import datetime
        start_timestamp = latest_match.get("game_start_timestamp", 0)
        end_timestamp = latest_match.get("game_end_timestamp", 0)
        
        start_time = None
        end_time = None
        if start_timestamp > 0:
            start_time = datetime.datetime.fromtimestamp(start_timestamp / 1000).isoformat()
        if end_timestamp > 0:
            end_time = datetime.datetime.fromtimestamp(end_timestamp / 1000).isoformat()
        
        return {
            "match_id": latest_match.get("match_id"),
            "champion": latest_match.get("champion"),
            "champion_level": latest_match.get("champion_level"),
            "kills": latest_match.get("kills"),
            "deaths": latest_match.get("deaths"),
            "assists": latest_match.get("assists"),
            "kda": latest_match.get("kda"),
            "game_mode": latest_match.get("game_mode"),
            "game_type": latest_match.get("game_type"),
            "queue_id": latest_match.get("queue_id"),
            "duration": duration_formatted,
            "duration_seconds": duration_seconds,
            "game_start_time": start_time,
            "game_end_time": end_time,
            "total_damage_dealt": latest_match.get("total_damage_dealt"),
            "total_damage_taken": latest_match.get("total_damage_taken"),
            "gold_earned": latest_match.get("gold_earned"),
            "cs_total": latest_match.get("cs_total"),
            "vision_score": latest_match.get("vision_score"),
            "items": latest_match.get("items", []),
            "win": latest_match.get("win"),
        }
