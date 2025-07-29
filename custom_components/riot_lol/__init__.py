"""The Riot LoL integration."""
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, DEFAULT_SCAN_INTERVAL
from .coordinator import RiotLoLDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Riot LoL from a config entry."""
    _LOGGER.debug("Setting up Riot LoL integration for entry: %s", entry.entry_id)
    
    config_type = entry.data.get("config_type", "summoner")
    
    if config_type == "api_key":
        # This is just an API key configuration, no setup needed
        _LOGGER.debug("API key configuration entry, no platform setup required")
        return True
    
    # This is a summoner configuration
    game_name = entry.data["game_name"]
    tag_line = entry.data.get("tag_line", "")
    region = entry.data["region"]
    puuid = entry.data.get("puuid")  # Get pre-validated PUUID if available
    
    # Get scan interval from options (with fallback to default)
    scan_interval = entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL)
    update_interval = timedelta(seconds=scan_interval)
    
    # Create data update coordinator (no API key needed here, it gets it dynamically)
    session = async_get_clientsession(hass)
    coordinator = RiotLoLDataUpdateCoordinator(
        hass=hass,
        game_name=game_name,
        tag_line=tag_line,
        region=region,
        session=session,
        update_interval=update_interval,
        puuid=puuid,  # Pass the pre-validated PUUID
    )

    # Perform initial data fetch
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator in hass data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Setup platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Setup options update listener
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading Riot LoL integration for entry: %s", entry.entry_id)
    
    config_type = entry.data.get("config_type", "summoner")
    
    if config_type == "api_key":
        # API key configuration, no platforms to unload
        return True
    
    # Summoner configuration, unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        
        # Remove domain data if no more entries
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)
    
    return unload_ok


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options for the config entry."""
    _LOGGER.debug("Updating options for Riot LoL entry: %s", entry.entry_id)
    
    config_type = entry.data.get("config_type", "summoner")
    
    if config_type == "api_key":
        # API key updated, trigger reload of all summoner coordinators
        _LOGGER.info("API key updated, triggering update for all summoner coordinators")
        for domain_entry in hass.config_entries.async_entries(DOMAIN):
            if (domain_entry.data.get("config_type") == "summoner" and 
                domain_entry.entry_id in hass.data.get(DOMAIN, {})):
                coordinator = hass.data[DOMAIN][domain_entry.entry_id]
                await coordinator.async_request_refresh()
        return
    
    # Summoner configuration options update
    if entry.entry_id not in hass.data.get(DOMAIN, {}):
        return
        
    # Get the coordinator
    coordinator: RiotLoLDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    # Update scan interval if changed
    new_scan_interval = entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL)
    new_update_interval = timedelta(seconds=new_scan_interval)
    
    if coordinator.update_interval != new_update_interval:
        coordinator.update_interval = new_update_interval
        _LOGGER.info("Updated scan interval to %s seconds", new_scan_interval)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Riot LoL component from YAML configuration."""
    # This integration only supports config entries
    return True
