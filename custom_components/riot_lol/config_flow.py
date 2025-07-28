import logging
from urllib.parse import quote
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from aiohttp import ClientSession, ClientResponseError, ClientTimeout

from .const import (
    DOMAIN,
    PLATFORM_REGIONS,
    REGION_CLUSTERS,
    DEFAULT_REGION,
    MIN_SCAN_INTERVAL,
    MAX_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

class RiotLoLConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return RiotLoLOptionsFlow(config_entry)

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Check if already configured
            riot_id = f"{user_input['game_name']}#{user_input['tag_line']}" if user_input['tag_line'] else user_input['game_name']
            await self.async_set_unique_id(f"{riot_id}_{user_input['region']}".lower())
            self._abort_if_unique_id_configured()
            
            api_key = user_input["api_key"]
            game_name = user_input["game_name"]
            tag_line = user_input["tag_line"] or ""  # Default to empty string if not provided
            region = user_input["region"]

            validation_result = await self._validate_input(api_key, game_name, tag_line, region)
            if validation_result["valid"]:
                # Store the data including both game_name/tag_line and riot_id for backward compatibility
                data = user_input.copy()
                data["riot_id"] = riot_id
                return self.async_create_entry(title=riot_id, data=data)
            else:
                errors["base"] = validation_result["error_code"]

        data_schema = vol.Schema({
            vol.Required("api_key"): str,
            vol.Required("game_name"): str,
            vol.Required("tag_line", default=""): str,
            vol.Required("region", default=DEFAULT_REGION): vol.In(PLATFORM_REGIONS),
        })
        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)

    async def _validate_input(self, api_key, game_name, tag_line, region):
        """Validate API key and Riot ID by fetching account info."""
        
        # Map platform regions to regional clusters for ACCOUNT-V1 API
        regional_cluster = REGION_CLUSTERS.get(region, "americas")
        
        # URL encode the game name and tag line to handle special characters
        encoded_game_name = quote(game_name, safe='')
        encoded_tag_line = quote(tag_line, safe='') if tag_line else ""
        
        # Use ACCOUNT-V1 API to get PUUID by Riot ID (recommended approach)
        url = f"https://{regional_cluster}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{encoded_game_name}/{encoded_tag_line}"
        headers = {"X-Riot-Token": api_key}
        
        timeout = ClientTimeout(total=10)  # 10 second timeout

        try:
            async with ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        account_data = await resp.json()
                        puuid = account_data.get("puuid")
                        if puuid:
                            _LOGGER.info(f"Successfully validated Riot ID: {game_name}#{tag_line} in region: {region}")
                            return {"valid": True, "error_code": None, "puuid": puuid}
                        else:
                            _LOGGER.error(f"No PUUID found in response for {game_name}#{tag_line}")
                            return {"valid": False, "error_code": "invalid_response"}
                    elif resp.status == 401:
                        _LOGGER.error(f"Invalid API key for region: {region}")
                        return {"valid": False, "error_code": "invalid_api_key"}
                    elif resp.status == 403:
                        _LOGGER.error(f"API key expired or insufficient permissions for region: {region}")
                        return {"valid": False, "error_code": "api_key_expired"}
                    elif resp.status == 404:
                        _LOGGER.error(f"Riot ID not found: {game_name}#{tag_line} in region: {region}")
                        return {"valid": False, "error_code": "riot_id_not_found"}
                    elif resp.status == 429:
                        _LOGGER.error(f"Rate limit exceeded for region: {region}")
                        return {"valid": False, "error_code": "rate_limit"}
                    else:
                        _LOGGER.error(f"Unexpected response status {resp.status} for {game_name}#{tag_line} in {region}")
                        return {"valid": False, "error_code": "unknown_error"}
                        
        except ClientResponseError as e:
            _LOGGER.error(f"HTTP error validating {game_name}#{tag_line}: {e}")
            return {"valid": False, "error_code": "connection_error"}
        except Exception as e:
            _LOGGER.error(f"Unexpected error validating {game_name}#{tag_line}: {e}")
            return {"valid": False, "error_code": "connection_error"}

    async def _fallback_validate_summoner_name(self, api_key, summoner_name, region):
        """Fallback validation using deprecated summoner name endpoint (for backward compatibility)."""
        _LOGGER.warning("Using deprecated summoner name endpoint as fallback")
        
        # URL encode the summoner name to handle special characters
        encoded_summoner_name = quote(summoner_name, safe='')
        url = f"https://{region}.api.riotgames.com/lol/summoner/v4/summoners/by-name/{encoded_summoner_name}"
        headers = {"X-Riot-Token": api_key}
        
        timeout = ClientTimeout(total=10)

        try:
            async with ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        summoner_data = await resp.json()
                        puuid = summoner_data.get("puuid")
                        if puuid:
                            _LOGGER.info(f"Successfully validated summoner: {summoner_name} in region: {region}")
                            return {"valid": True, "error_code": None, "puuid": puuid}
                        else:
                            return {"valid": False, "error_code": "invalid_response"}
                    elif resp.status == 404:
                        return {"valid": False, "error_code": "summoner_not_found"}
                    else:
                        return {"valid": False, "error_code": "connection_error"}
        except Exception as e:
            _LOGGER.error(f"Fallback validation failed for {summoner_name}: {e}")
            return {"valid": False, "error_code": "connection_error"}


class RiotLoLOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Riot LoL integration."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        # Note: self.config_entry is automatically set by parent class
        # No need to explicitly set it (deprecated in HA 2025.12)

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    "scan_interval",
                    default=self.config_entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL)
                ): vol.All(vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL)),
            })
        )
