import logging
from urllib.parse import quote
import voluptuous as vol
from homeassistant import config_entries, data_entry_flow
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
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
    VERSION = 2

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return RiotLoLOptionsFlow(config_entry)

    async def async_step_user(self, user_input=None):
        """Handle the initial setup - choose between API key setup or summoner setup."""
        # Check if we already have a global API key configuration
        existing_api_config = None
        for entry in self._async_current_entries():
            if entry.data.get("config_type") == "api_key":
                existing_api_config = entry
                break

        if existing_api_config is None:
            # No API key configured yet, must set up API key first
            return await self.async_step_api_key()
        else:
            # API key exists, proceed to summoner setup
            return await self.async_step_summoner()

    async def async_step_api_key(self, user_input=None):
        """Handle API key configuration."""
        errors = {}

        if user_input is not None:
            api_key = user_input["api_key"]
            send_notifications = user_input.get("Key expiration notifications", True)
            api_key_24h_type = user_input.get("24-hour API key reminders", True)
            
            # Validate API key by making a test request
            validation_result = await self._validate_api_key(api_key)
            if validation_result["valid"]:
                # Create API key configuration entry with update timestamp
                from datetime import datetime
                return self.async_create_entry(
                    title="Riot Games API Key",
                    data={
                        "config_type": "api_key",
                        "api_key": api_key,
                    },
                    options={
                        "send_notifications": send_notifications,
                        "api_key_24h_type": api_key_24h_type,
                        "api_key_update_time": datetime.now().isoformat(),
                    }
                )
            else:
                errors["api_key"] = validation_result["error"]

        data_schema = vol.Schema({
            vol.Required("api_key"): str,
            vol.Optional("Key expiration notifications", default=True): bool,
            vol.Optional("24-hour API key reminders", default=True): bool,
        })

        return self.async_show_form(
            step_id="api_key",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "api_url": "https://developer.riotgames.com/",
            }
        )

    async def async_step_summoner(self, user_input=None):
        """Handle summoner configuration (no API key needed)."""
        errors = {}

        if user_input is not None:
            # Check if already configured
            riot_id = f"{user_input['game_name']}#{user_input['tag_line']}" if user_input['tag_line'] else user_input['game_name']
            await self.async_set_unique_id(f"{riot_id}_{user_input['region']}".lower())
            self._abort_if_unique_id_configured()
            
            game_name = user_input["game_name"]
            tag_line = user_input["tag_line"] or ""
            region = user_input["region"]

            # Get API key from existing config
            api_key = await self._get_global_api_key()
            if not api_key:
                return self.async_abort(reason="no_api_key")

            validation_result = await self._validate_input(api_key, game_name, tag_line, region)
            if validation_result["valid"]:
                # Store summoner data (no API key stored here)
                data = {
                    "config_type": "summoner",
                    "game_name": game_name,
                    "tag_line": tag_line,
                    "region": region,
                    "riot_id": riot_id,
                    "puuid": validation_result["puuid"],
                    "scan_interval": user_input.get("scan_interval", DEFAULT_SCAN_INTERVAL),
                }
                return self.async_create_entry(title=riot_id, data=data)
            else:
                errors["base"] = validation_result["error_code"]

        data_schema = vol.Schema({
            vol.Required("game_name"): str,
            vol.Required("tag_line", default=""): str,
            vol.Required("region", default=DEFAULT_REGION): vol.In(PLATFORM_REGIONS),
            vol.Optional("scan_interval", default=DEFAULT_SCAN_INTERVAL): vol.All(
                vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL)
            ),
        })
        return self.async_show_form(step_id="summoner", data_schema=data_schema, errors=errors)

    async def _get_global_api_key(self):
        """Get the global API key from existing configuration."""
        for entry in self.hass.config_entries.async_entries(DOMAIN):
            if entry.data.get("config_type") == "api_key":
                return entry.data.get("api_key")
        return None

    async def _validate_api_key(self, api_key):
        """Validate API key by making a test request."""
        url = "https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/test/user"
        headers = {"X-Riot-Token": api_key}
        
        try:
            timeout = ClientTimeout(total=10)
            async with ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 401:
                        return {"valid": False, "error": "invalid_api_key"}
                    elif response.status == 403:
                        return {"valid": False, "error": "forbidden_api_key"}
                    elif response.status == 404:
                        # 404 is expected for test user, means API key is valid
                        return {"valid": True}
                    elif response.status == 429:
                        return {"valid": False, "error": "rate_limit"}
                    else:
                        # Any other response means API key is probably valid
                        return {"valid": True}
        except Exception as err:
            _LOGGER.error("Error validating API key: %s", err)
            return {"valid": False, "error": "connection_error"}

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
        
        _LOGGER.info(f"Validating Riot ID: {game_name}#{tag_line} in region {region}")
        _LOGGER.info(f"Using regional cluster: {regional_cluster}")
        _LOGGER.info(f"API URL (masked): https://{regional_cluster}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/***/***/")
        
        timeout = ClientTimeout(total=10)  # 10 second timeout

        try:
            async with ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers) as resp:
                    _LOGGER.info(f"Account API response status: {resp.status}")
                    if resp.status == 200:
                        account_data = await resp.json()
                        _LOGGER.info(f"Account API response data: {account_data}")
                        puuid = account_data.get("puuid")
                        if puuid:
                            _LOGGER.info(f"Successfully validated Riot ID: {game_name}#{tag_line} in region: {region}")
                            return {"valid": True, "error_code": None, "puuid": puuid}
                        else:
                            _LOGGER.error(f"No PUUID found in response for {game_name}#{tag_line}")
                            _LOGGER.error(f"Available fields in response: {list(account_data.keys()) if account_data else 'None'}")
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
        _LOGGER.error("=== OPTIONS INIT STEP CALLED ===")
        config_type = self.config_entry.data.get("config_type", "summoner")
        _LOGGER.error(f"Config type: {config_type}, User input: {user_input}")
        
        if config_type == "api_key":
            _LOGGER.error("Routing to API key options")
            return await self.async_step_api_key_options(user_input)
        else:
            _LOGGER.error("Routing to summoner options")
            return await self.async_step_summoner_options(user_input)

    async def async_step_api_key_options(self, user_input=None):
        """Handle API key options."""
        _LOGGER.error("=== API KEY OPTIONS STEP CALLED ===")
        
        if user_input is not None:
            _LOGGER.error("=== USER INPUT RECEIVED ===")
            # Extract values from user input with logging
            new_api_key = user_input["api_key"]
            send_notifications = user_input.get("Key expiration notifications", True)
            api_key_24h_type = user_input.get("24-hour API key reminders", True)
            
            _LOGGER.error(f"User Input: {user_input}")
            _LOGGER.error(f"Extracted - notifications: {send_notifications}, 24h: {api_key_24h_type}")
            
            # Check if API key has changed
            current_api_key = self.config_entry.data.get("api_key", "")
            api_key_changed = new_api_key != current_api_key
            
            if api_key_changed:
                # Validate new API key only if it changed
                validation_result = await self._validate_api_key(new_api_key)
                if not validation_result["valid"]:
                    errors = {"api_key": validation_result["error"]}
                    return self.async_show_form(
                        step_id="api_key_options",
                        data_schema=vol.Schema({
                            vol.Required("api_key", default=self.config_entry.data.get("api_key", "")): str,
                            vol.Optional("Key expiration notifications", default=send_notifications): bool,
                            vol.Optional("24-hour API key reminders", default=api_key_24h_type): bool,
                        }),
                        errors=errors
                    )
            
            # Update config entry - always update options, update data only if API key changed
            from datetime import datetime
            new_options = {
                "send_notifications": send_notifications,
                "api_key_24h_type": api_key_24h_type,
            }
            
            _LOGGER.error(f"Preparing to save options: {new_options}")
            
            if api_key_changed:
                # Update both data and options with new timestamp
                new_data = self.config_entry.data.copy()
                new_data["api_key"] = new_api_key
                new_options["api_key_update_time"] = datetime.now().isoformat()  # Reset timer when key is updated
                _LOGGER.error(f"API key changed - updating data and options")
                self.hass.config_entries.async_update_entry(
                    self.config_entry, 
                    data=new_data,
                    options=new_options
                )
            else:
                # Only update options, preserve existing api_key_update_time
                existing_options = self.config_entry.options.copy()
                existing_options.update(new_options)
                _LOGGER.error(f"API key unchanged - updating only options: {existing_options}")
                self.hass.config_entries.async_update_entry(
                    self.config_entry, 
                    options=existing_options
                )
            
            _LOGGER.error("=== OPTIONS UPDATE COMPLETED ===")
            return self.async_create_entry(title="", data={})

        # Show form with current values
        current_notifications = self.config_entry.options.get("send_notifications", True)
        current_24h = self.config_entry.options.get("api_key_24h_type", True)
        _LOGGER.error(f"Showing form - current notifications: {current_notifications}, 24h: {current_24h}")
        
        return self.async_show_form(
            step_id="api_key_options",
            data_schema=vol.Schema({
                vol.Required("api_key", default=self.config_entry.data.get("api_key", "")): str,
                vol.Optional("Key expiration notifications", default=current_notifications): bool,
                vol.Optional("24-hour API key reminders", default=current_24h): bool,
            }),
            description_placeholders={
                "current_notifications": str(current_notifications),
                "current_24h": str(current_24h),
            }
        )

    async def async_step_summoner_options(self, user_input=None):
        """Handle summoner options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="summoner_options",
            data_schema=vol.Schema({
                vol.Optional(
                    "scan_interval",
                    default=self.config_entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL)
                ): vol.All(vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL)),
            })
        )

    async def _validate_api_key(self, api_key):
        """Validate API key by making a test request."""
        url = "https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/test/user"
        headers = {"X-Riot-Token": api_key}
        
        try:
            timeout = ClientTimeout(total=10)
            async with ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 401:
                        return {"valid": False, "error": "invalid_api_key"}
                    elif response.status == 403:
                        return {"valid": False, "error": "forbidden_api_key"}
                    elif response.status == 404:
                        # 404 is expected for test user, means API key is valid
                        return {"valid": True}
                    elif response.status == 429:
                        return {"valid": False, "error": "rate_limit"}
                    else:
                        # Any other response means API key is probably valid
                        return {"valid": True}
        except Exception as err:
            _LOGGER.error("Error validating API key: %s", err)
            return {"valid": False, "error": "connection_error"}
