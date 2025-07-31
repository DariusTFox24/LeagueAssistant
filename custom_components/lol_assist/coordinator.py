"""
Data update coordinator for LeagueAssistant - Unofficial League of Legends Integration.

LeagueAssistant is not affiliated with Riot Games, Inc. or League of Legends.
This is an independent, community-created integration that uses the public Riot Games API.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from urllib.parse import quote

from aiohttp import ClientSession, ClientResponseError, ClientTimeout
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import REGION_CLUSTERS, GAME_STATES, DEFAULT_SCAN_INTERVAL, QUEUE_TYPES, GAME_MODES, CHAMPION_NAMES, MAP_NAMES, GAME_TYPES

_LOGGER = logging.getLogger(__name__)


def format_game_duration(seconds: int) -> str:
    """Format game duration from seconds to human readable format."""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:  # Less than 1 hour
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds}s"
    else:  # 1 hour or more
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        remaining_seconds = seconds % 60
        return f"{hours}h {minutes}m {remaining_seconds}s"


def format_game_start_time(epoch_ms: int) -> str:
    """Format game start time from epoch milliseconds to human readable format."""
    try:
        # Convert milliseconds to seconds
        timestamp = epoch_ms / 1000
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, OSError):
        return "Unknown"


class RiotLoLDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Riot LoL data."""

    def __init__(
        self,
        hass: HomeAssistant,
        game_name: str,
        tag_line: str,
        region: str,
        session: ClientSession = None,
        update_interval: timedelta = timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        puuid: Optional[str] = None,
    ):
        """Initialize the coordinator."""
        self._hass = hass
        self._game_name = game_name
        self._tag_line = tag_line
        self._region = region
        self._session = session or async_get_clientsession(hass)
        self._puuid: Optional[str] = puuid  # Use pre-validated PUUID if available
        self._summoner_id: Optional[str] = None
        self._last_match_id: Optional[str] = None
        self._last_match_data: Optional[Dict[str, Any]] = None
        self._match_history: Optional[list] = None
        self._last_successful_data: Optional[Dict[str, Any]] = None
        self._consecutive_errors = 0
        self._max_errors = 5
        
        riot_id = f"{game_name}#{tag_line}" if tag_line else game_name
        
        super().__init__(
            hass,
            _LOGGER,
            name=f"Riot LoL Data for {riot_id}",
            update_interval=update_interval,
        )

    def _get_api_key(self) -> Optional[str]:
        """Get the global API key from configuration."""
        from .const import DOMAIN
        for entry in self._hass.config_entries.async_entries(DOMAIN):
            if entry.data.get("config_type") == "api_key":
                return entry.data.get("api_key")
        return None

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with API key."""
        api_key = self._get_api_key()
        if not api_key:
            raise UpdateFailed("No API key available")
        return {"X-Riot-Token": api_key}
        
        if self._puuid:
            _LOGGER.info(f"Using pre-validated PUUID for {riot_id}: {self._puuid[:8]}...")
        else:
            _LOGGER.info(f"No pre-validated PUUID, will fetch account info for {riot_id}")

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from Riot API."""
        _LOGGER.info("Starting data update cycle...")
        
        # Check if API key is available
        api_key = self._get_api_key()
        if not api_key:
            raise UpdateFailed("No API key configured. Please set up the Riot Games API key first.")
        
        try:
            # Initialize PUUID if not set
            if not self._puuid:
                _LOGGER.info("No PUUID cached, fetching account info...")
                try:
                    await self._fetch_account_info()
                except UpdateFailed as err:
                    _LOGGER.error("Failed to fetch account info: %s", err)
                    raise
            else:
                _LOGGER.debug("Using cached PUUID: %s", self._puuid[:8] + "...")
            
            # Fetch match history and latest match data first
            try:
                _LOGGER.debug("Fetching match history...")
                await self._fetch_match_history()
            except Exception as err:
                _LOGGER.warning("Error fetching match history: %s", err)
            
            # Check player status and current game
            player_status = None
            current_game_data = None
            try:
                _LOGGER.debug("Checking for current game first...")
                current_game = await self._fetch_current_game()
                if current_game:
                    _LOGGER.info("Player is currently in League of Legends game - processing game data")
                    current_game_data = await self._process_current_game(current_game)
                    player_status = "in_game"
                    _LOGGER.info("Current game data processed successfully: state=%s, game_mode=%s, champion=%s", 
                               current_game_data.get("state"), 
                               current_game_data.get("game_mode"), 
                               current_game_data.get("champion"))
                else:
                    _LOGGER.debug("Player not in current game, checking recent activity...")
                    player_status = await self._fetch_player_status()
                    
                    # Double-check: If previous state was "In Game" and now it's "Played Recently",
                    # wait a moment and check again to ensure the game actually ended
                    if (hasattr(self, '_last_successful_data') and self._last_successful_data and 
                        self._last_successful_data.get("state") == "In Game" and 
                        player_status == "recently_played"):
                        _LOGGER.info("Status changed from 'In Game' to 'Played Recently' - double-checking...")
                        await asyncio.sleep(3)  # Wait 3 seconds
                        double_check_game = await self._fetch_current_game()
                        if double_check_game:
                            _LOGGER.info("Double-check found player still in game - keeping 'In Game' status")
                            current_game_data = await self._process_current_game(double_check_game)
                            player_status = "in_game"
                        else:
                            _LOGGER.info("Double-check confirmed game ended - status is 'Played Recently'")
                    
                    _LOGGER.info("Player status: %s", player_status)
            except Exception as err:
                _LOGGER.warning("Error checking player status: %s", err)
                player_status = "unknown"
            
            # Fetch ranked stats
            ranked_stats = {}
            try:
                _LOGGER.debug("Fetching ranked stats...")
                ranked_stats = await self._fetch_ranked_stats()
            except Exception as err:
                _LOGGER.warning("Error fetching ranked stats: %s", err)
                ranked_stats = {"rank": "Unknown"}
            
            # Fetch summoner level
            _LOGGER.debug("Fetching summoner level...")
            summoner_level = await self._fetch_summoner_level()
            
            self._consecutive_errors = 0  # Reset error counter on success
            
            # Build comprehensive data combining current game, latest match, and ranked stats
            _LOGGER.debug("Building comprehensive data...")
            result = self._build_comprehensive_data(current_game_data, ranked_stats, summoner_level, player_status)
            
            # Cache successful result
            self._last_successful_data = result.copy()
            
            _LOGGER.info("Data update completed successfully")
            return result
            
        except UpdateFailed:
            # Re-raise UpdateFailed exceptions (these are expected)
            _LOGGER.warning("Update failed, but continuing with available data")
            raise
        except Exception as err:
            self._consecutive_errors += 1
            _LOGGER.error("Unexpected error in coordinator update (attempt %d/%d): %s", 
                         self._consecutive_errors, self._max_errors, err, exc_info=True)
            
            if self._consecutive_errors >= self._max_errors:
                _LOGGER.error(
                    "Too many consecutive errors (%d), marking as offline: %s",
                    self._consecutive_errors,
                    err
                )
                # Return minimal data instead of failing completely
                return {
                    "state": GAME_STATES["offline"],
                    "last_updated": datetime.now().isoformat(),
                    "error": str(err),
                    "summoner_level": 0,
                    "rank": "Unknown",
                    "champion": "Error",
                    "kills": 0,
                    "deaths": 0,
                    "assists": 0,
                    "kda": 0.0,
                    "latest_match_id": None,
                }
            
            # For fewer errors, return cached data if available or minimal data
            if hasattr(self, '_last_successful_data') and self._last_successful_data:
                _LOGGER.warning("Returning cached data due to error")
                return self._last_successful_data
            
            raise UpdateFailed(f"Error communicating with Riot API: {err}")

    async def _fetch_account_info(self) -> None:
        """Fetch account info using Riot ID."""
        regional_cluster = REGION_CLUSTERS.get(self._region, "americas")
        
        encoded_game_name = quote(self._game_name, safe='')
        encoded_tag_line = quote(self._tag_line, safe='') if self._tag_line else ""
        
        url = f"https://{regional_cluster}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{encoded_game_name}/{encoded_tag_line}"
        headers = self._get_headers()
        timeout = ClientTimeout(total=10)
        
        _LOGGER.info("Fetching account info for %s#%s in region %s (cluster: %s)", 
                    self._game_name, self._tag_line, self._region, regional_cluster)
        _LOGGER.info("Account API URL structure: https://%s.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{gameName}/{tagLine}", regional_cluster)
        
        try:
            async with self._session.get(url, headers=headers, timeout=timeout) as response:
                if response.status == 200:
                    data = await response.json()
                    _LOGGER.debug("Account API response for %s#%s: %s", 
                                self._game_name, self._tag_line, 
                                {k: v[:8] + "..." if k == "puuid" and v else v for k, v in data.items()})
                    
                    puuid = data.get("puuid")
                    if puuid and len(puuid) > 0:
                        self._puuid = puuid
                        _LOGGER.debug("Retrieved PUUID: %s", self._puuid[:8] + "...")
                    else:
                        available_fields = list(data.keys()) if data else []
                        _LOGGER.error("Account API response missing valid 'puuid' field. Available fields: %s", available_fields)
                        raise UpdateFailed(f"No PUUID found in account response. Available fields: {available_fields}")
                elif response.status == 429:
                    raise UpdateFailed("Rate limit exceeded")
                elif response.status == 401:
                    raise UpdateFailed("Invalid API key")
                elif response.status == 404:
                    raise UpdateFailed(f"Riot ID not found: {self._game_name}#{self._tag_line}")
                else:
                    raise UpdateFailed(f"API error: {response.status}")
                    
        except ClientResponseError as err:
            raise UpdateFailed(f"HTTP error fetching account info: {err}")
        except KeyError as err:
            raise UpdateFailed(f"Missing expected field in account response: {err}")
        except Exception as err:
            raise UpdateFailed(f"Unexpected error fetching account info: {err}")

    async def _fetch_summoner_info(self) -> None:
        """Fetch summoner info using PUUID."""
        if not self._puuid:
            await self._fetch_account_info()
            
        if not self._puuid or len(self._puuid) < 10:
            raise UpdateFailed(f"Invalid PUUID: {self._puuid}. Cannot fetch summoner info.")
            
        url = f"https://{self._region}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{self._puuid}"
        headers = self._get_headers()
        timeout = ClientTimeout(total=10)
        
        _LOGGER.info("Fetching summoner info for PUUID %s in region %s", self._puuid[:8] + "...", self._region)
        _LOGGER.info("Summoner API URL: %s", url.replace(self._puuid, self._puuid[:8] + "..."))
        
        try:
            async with self._session.get(url, headers=headers, timeout=timeout) as response:
                if response.status == 200:
                    data = await response.json()
                    _LOGGER.info("Full summoner API response for debugging: %s", data)
                    
                    # Check for summoner ID in response (primary approach)
                    summoner_id = data.get("id")
                    if summoner_id:
                        self._summoner_id = summoner_id
                        _LOGGER.info("Successfully retrieved summoner ID: %s", self._summoner_id)
                    else:
                        # Log available fields and try alternative approaches
                        available_fields = list(data.keys()) if data else []
                        _LOGGER.error("Summoner API response missing 'id' field. Available fields: %s", available_fields)
                        _LOGGER.error("This might indicate an API issue or regional problem. Response: %s", data)
                        
                        # Try alternative field names that might contain the summoner ID
                        alt_id = data.get("summonerId") or data.get("encryptedSummonerId")
                        if alt_id:
                            self._summoner_id = alt_id
                            _LOGGER.info("Using alternative summoner ID field: %s", self._summoner_id)
                        else:
                            # Continue without summoner ID and use PUUID where possible
                            _LOGGER.warning("No summoner ID available, will use PUUID where possible")
                            _LOGGER.warning("Some features (current game, ranked stats) may not work")
                            self._summoner_id = None
                elif response.status == 404:
                    _LOGGER.warning("Summoner not found for PUUID %s... in region %s", self._puuid[:8], self._region)
                    # Don't fail completely, just continue without summoner ID
                    self._summoner_id = None
                    return
                elif response.status == 429:
                    _LOGGER.warning("Rate limit exceeded for summoner lookup")
                    return
                elif response.status == 401:
                    _LOGGER.warning("Invalid API key for summoner lookup")
                    return
                else:
                    _LOGGER.warning("API error fetching summoner: %s", response.status)
                    return
                    
        except ClientResponseError as err:
            _LOGGER.warning("HTTP error fetching summoner info: %s", err)
        except KeyError as err:
            _LOGGER.warning("Missing expected field in summoner response: %s", err)
        except Exception as err:
            _LOGGER.warning("Unexpected error fetching summoner info: %s", err)

    async def _fetch_current_game(self) -> Optional[Dict[str, Any]]:
        """Check if player is currently in a game using PUUID (modern approach) with retry logic."""
        if not self._puuid:
            _LOGGER.debug("No PUUID available, skipping current game check")
            return None
            
        url = f"https://{self._region}.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{self._puuid}"
        headers = self._get_headers()
        timeout = ClientTimeout(total=15)  # Increased timeout
        
        _LOGGER.debug("Checking current game with PUUID endpoint: %s", url.replace(self._puuid, self._puuid[:8] + "..."))
        
        # Try with retry logic for temporary failures
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                async with self._session.get(url, headers=headers, timeout=timeout) as response:
                    if response.status == 200:
                        game_data = await response.json()
                        _LOGGER.info("Player is currently in game (PUUID endpoint) - attempt %d", attempt + 1)
                        return game_data
                    elif response.status == 404:
                        # Not in game - this is definitive
                        _LOGGER.debug("Player is not currently in game (PUUID endpoint) - attempt %d", attempt + 1)
                        return None
                    elif response.status == 429:
                        if attempt < max_retries:
                            _LOGGER.warning("Rate limit exceeded for current game check, retrying in %d seconds...", (attempt + 1) * 2)
                            await asyncio.sleep((attempt + 1) * 2)  # Progressive backoff
                            continue
                        else:
                            _LOGGER.warning("Rate limit exceeded for current game check after %d attempts", max_retries + 1)
                            return None
                    else:
                        if attempt < max_retries:
                            _LOGGER.warning("Error checking current game (status %d), retrying...", response.status)
                            await asyncio.sleep(1)
                            continue
                        else:
                            _LOGGER.warning("Error checking current game after %d attempts: %s", max_retries + 1, response.status)
                            return None
                        
            except asyncio.TimeoutError:
                if attempt < max_retries:
                    _LOGGER.warning("Timeout checking current game, retrying...")
                    await asyncio.sleep(1)
                    continue
                else:
                    _LOGGER.warning("Timeout checking current game after %d attempts", max_retries + 1)
                    return None
            except ClientResponseError as err:
                if attempt < max_retries:
                    _LOGGER.warning("HTTP error checking current game: %s, retrying...", err)
                    await asyncio.sleep(1)
                    continue
                else:
                    _LOGGER.warning("HTTP error checking current game after %d attempts: %s", max_retries + 1, err)
                    return None
            except Exception as err:
                if attempt < max_retries:
                    _LOGGER.warning("Unexpected error checking current game: %s, retrying...", err)
                    await asyncio.sleep(1)
                    continue
                else:
                    _LOGGER.warning("Unexpected error checking current game after %d attempts: %s", max_retries + 1, err)
                    return None
        
        return None

    async def _process_current_game(self, game_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process current game data."""
        try:
            # Find the player in the participants
            participant = None
            participants = game_data.get("participants", [])
            _LOGGER.debug("Looking for player in %d participants", len(participants))
            _LOGGER.debug("Searching for PUUID: %s, Summoner ID: %s, Game Name: %s", 
                         self._puuid[:8] + "..." if self._puuid else "None",
                         self._summoner_id or "None", 
                         self._game_name)
            
            # Primary search by PUUID (most reliable)
            for p in participants:
                if self._puuid and p.get("puuid") == self._puuid:
                    participant = p
                    _LOGGER.info("Found player by PUUID match")
                    break
                elif self._summoner_id and p.get("summonerId") == self._summoner_id:
                    participant = p
                    _LOGGER.info("Found player by Summoner ID match")
                    break
            
            if not participant:
                # Try to find by summoner name as fallback
                _LOGGER.debug("Primary match failed, trying summoner name fallback")
                for i, p in enumerate(participants):
                    summoner_name = p.get("summonerName", "")
                    _LOGGER.debug("Participant %d: summonerName='%s', championId=%s", 
                                 i, summoner_name, p.get("championId"))
                    if summoner_name.lower() == self._game_name.lower():
                        participant = p
                        _LOGGER.info("Found player by summoner name match: %s", summoner_name)
                        break
            
            if not participant:
                _LOGGER.error("Player not found in current game data")
                _LOGGER.debug("Available participants: %s", 
                             [{"summonerName": p.get("summonerName"), "puuid": p.get("puuid", "")[:8] + "..." if p.get("puuid") else "None"} 
                              for p in participants])
                raise UpdateFailed("Player not found in current game data")
            
            # Get champion info
            champion_id = participant.get("championId", 0)
            champion_name = participant.get("championName")
            
            # If championName is not provided, try to get it from championId
            if not champion_name or champion_name == "Unknown":
                champion_name = CHAMPION_NAMES.get(champion_id, f"Champion_{champion_id}")
                _LOGGER.debug("Resolved champion name from ID %d: %s", champion_id, champion_name)
            
            _LOGGER.debug("Final champion info: ID=%d, Name='%s'", champion_id, champion_name)
            
            # Get queue and game mode info
            queue_id = game_data.get("gameQueueConfigId", 0)
            raw_game_mode = game_data.get("gameMode", "Unknown")
            map_id = game_data.get("mapId", 0)
            game_type = game_data.get("gameType", "Unknown")
            game_start_time_ms = game_data.get("gameStartTime", 0)
            game_length_seconds = game_data.get("gameLength", 0)
            
            # Map to human-readable names
            queue_name = QUEUE_TYPES.get(queue_id, f"Queue {queue_id}")
            game_mode_name = GAME_MODES.get(raw_game_mode, raw_game_mode)
            map_name = MAP_NAMES.get(map_id, f"Map {map_id}")
            game_type_name = GAME_TYPES.get(game_type, game_type)
            
            # Format times to human-readable
            game_start_time_formatted = format_game_start_time(game_start_time_ms)
            game_duration_formatted = format_game_duration(game_length_seconds)
            
            _LOGGER.info("Current game: %s (Queue %d: %s), Champion: %s (ID: %d), Map: %s, Duration: %s", 
                        game_mode_name, queue_id, queue_name, champion_name, champion_id, map_name, game_duration_formatted)
            
            return {
                "state": GAME_STATES.get("in_game", "In Game"),
                "game_mode": game_mode_name,
                "queue_type": queue_name,
                "queue_id": queue_id,
                "map_name": map_name,
                "map_id": map_id,
                "game_type": game_type_name,
                "champion": champion_name,
                "champion_id": champion_id,
                "game_start_time": game_start_time_ms,  # Keep raw for calculations
                "game_start_time_formatted": game_start_time_formatted,  # Human readable
                "game_length": game_length_seconds,  # Keep raw for calculations
                "game_duration": game_duration_formatted,  # Human readable
                "last_updated": datetime.now().isoformat(),
                "match_id": str(game_data.get("gameId", "")),
                # Current game doesn't have kill/death stats, set defaults
                "kills": 0,
                "deaths": 0,
                "assists": 0,
                "kda": 0.0,
            }
        except Exception as err:
            _LOGGER.error("Error processing current game data: %s", err)
            raise UpdateFailed(f"Failed to process current game: {err}")

    async def _fetch_latest_match_data(self) -> Optional[Dict[str, Any]]:
        """Fetch data from the latest match."""
        if not self._puuid:
            return None
            
        # Get regional cluster for match API
        regional_cluster = REGION_CLUSTERS.get(self._region, "americas")
        
        # Get latest match ID
        url = f"https://{regional_cluster}.api.riotgames.com/lol/match/v5/matches/by-puuid/{self._puuid}/ids?start=0&count=1"
        headers = self._get_headers()
        timeout = ClientTimeout(total=10)
        
        try:
            async with self._session.get(url, headers=headers, timeout=timeout) as response:
                if response.status != 200:
                    _LOGGER.warning("Error fetching match list: %s", response.status)
                    return None
                    
                match_ids = await response.json()
                if not match_ids:
                    return None
                
                latest_match_id = match_ids[0]
                
                # Skip if same as last processed match
                if latest_match_id == self._last_match_id:
                    return None
                
                # Fetch match details
                match_data = await self._fetch_match_details(latest_match_id, regional_cluster)
                if match_data:
                    self._last_match_id = latest_match_id
                    return match_data
                    
        except ClientResponseError as err:
            _LOGGER.warning("HTTP error fetching match data: %s", err)
            
        return None

    async def _fetch_match_details(self, match_id: str, regional_cluster: str) -> Optional[Dict[str, Any]]:
        """Fetch detailed match information."""
        url = f"https://{regional_cluster}.api.riotgames.com/lol/match/v5/matches/{match_id}"
        headers = self._get_headers()
        timeout = ClientTimeout(total=10)
        
        try:
            async with self._session.get(url, headers=headers, timeout=timeout) as response:
                if response.status != 200:
                    _LOGGER.warning("Error fetching match details: %s", response.status)
                    return None
                    
                match_data = await response.json()
                return self._process_match_data(match_data)
                
        except ClientResponseError as err:
            _LOGGER.warning("HTTP error fetching match details: %s", err)
            return None

    def _process_match_data(self, match_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process match data to extract player stats."""
        # Find player's participant data
        participant = None
        for p in match_data["info"]["participants"]:
            if p.get("puuid") == self._puuid:
                participant = p
                break
        
        if not participant:
            raise UpdateFailed("Player not found in match data")
        
        kills = participant.get("kills", 0)
        deaths = participant.get("deaths", 0)
        assists = participant.get("assists", 0)
        
        # Calculate KDA ratio
        kda = (kills + assists) / max(deaths, 1)  # Avoid division by zero
        
        return {
            "state": GAME_STATES["online"],
            "kills": kills,
            "deaths": deaths,
            "assists": assists,
            "kda": round(kda, 2),
            "champion": participant.get("championName", "Unknown"),
            "champion_level": participant.get("champLevel", 0),
            "game_mode": match_data["info"].get("gameMode", "Unknown"),
            "queue_type": match_data["info"].get("queueId"),
            "game_duration": match_data["info"].get("gameDuration", 0),
            "win": participant.get("win", False),
            "match_id": match_data["metadata"]["matchId"],
            "last_updated": datetime.now().isoformat(),
        }

    async def _fetch_ranked_stats(self) -> Dict[str, Any]:
        """Fetch ranked statistics using PUUID."""
        if not self._puuid:
            _LOGGER.warning("No PUUID available, cannot fetch ranked stats")
            return {"rank": "Unknown - No PUUID"}
            
        # Use PUUID-based league endpoint (newer, more reliable)
        url = f"https://{self._region}.api.riotgames.com/lol/league/v4/entries/by-puuid/{self._puuid}"
        headers = self._get_headers()
        timeout = ClientTimeout(total=10)
        
        _LOGGER.info("Fetching ranked stats for PUUID %s in region %s", self._puuid[:8] + "...", self._region)
        
        try:
            async with self._session.get(url, headers=headers, timeout=timeout) as response:
                if response.status == 200:
                    ranked_data = await response.json()
                    _LOGGER.info("Ranked API response: %s", ranked_data)
                    
                    # Find Solo/Duo queue stats
                    solo_queue = None
                    for queue in ranked_data:
                        if queue.get("queueType") == "RANKED_SOLO_5x5":
                            solo_queue = queue
                            break
                    
                    if solo_queue:
                        wins = solo_queue.get("wins", 0)
                        losses = solo_queue.get("losses", 0)
                        total_games = wins + losses
                        win_rate = (wins / total_games * 100) if total_games > 0 else 0
                        
                        return {
                            "rank": f"{solo_queue.get('tier', 'Unranked')} {solo_queue.get('rank', '')}".strip(),
                            "wins": wins,
                            "losses": losses,
                            "win_rate": round(win_rate, 1),
                            "league_points": solo_queue.get("leaguePoints", 0),
                        }
                    else:
                        return {"rank": "Unranked"}
                elif response.status == 404:
                    _LOGGER.info("No ranked data found (unranked player)")
                    return {"rank": "Unranked"}
                elif response.status == 429:
                    _LOGGER.warning("Rate limit exceeded for ranked stats")
                    return {"rank": "Rate Limited"}
                else:
                    _LOGGER.warning("Error fetching ranked stats: %s", response.status)
                    return {"rank": "Unknown"}
                    
        except ClientResponseError as err:
            _LOGGER.warning("HTTP error fetching ranked stats: %s", err)
            return {"rank": "Error"}
        except Exception as err:
            _LOGGER.warning("Unexpected error fetching ranked stats: %s", err)
            return {"rank": "Unknown"}
                    
        except ClientResponseError as err:
            _LOGGER.warning("HTTP error fetching ranked stats: %s", err)
            
        return {"rank": "Unknown"}

    async def _fetch_player_status(self) -> str:
        """Fetch player status based on recent activity (not including current game check)."""
        # Check recent activity from last match
        if self._last_match_data:
            last_match_timestamp = self._last_match_data.get("game_end_timestamp", 0)
            if last_match_timestamp > 0:
                import time
                current_time = int(time.time() * 1000)  # Convert to milliseconds
                time_diff_hours = (current_time - last_match_timestamp) / (1000 * 60 * 60)  # Convert to hours
                
                if time_diff_hours <= 4:
                    _LOGGER.info("Last match was %.1f hours ago - Played Recently", time_diff_hours)
                    return "recently_played"
                else:
                    _LOGGER.info("Last match was %.1f hours ago - Touching Grass", time_diff_hours)
                    return "touching_grass"
        
        # If no match data available, check if we have any match history
        if self._match_history and len(self._match_history) > 0:
            # We have match history but no recent match data processed yet
            # Default to recently played until we get match details
            _LOGGER.debug("Have match history but no processed match data yet")
            return "recently_played"
        
        # No match data at all - probably touching grass
        _LOGGER.debug("No match history found - likely touching grass")
        return "touching_grass"

    async def _check_other_riot_games(self) -> Optional[str]:
        """Check if player is in other Riot games (TFT, Valorant)."""
        # Note: This is a placeholder for future enhancement
        # The Riot API doesn't currently provide cross-game status easily
        # For now, we can only reliably detect League of Legends games
        
        # Future implementation could check:
        # - TFT active games API (if available)
        # - Valorant status (if API becomes available)
        # - Recent match history from other games
        
        _LOGGER.debug("Cross-game detection not yet implemented")
        return None

    async def _fetch_match_history(self) -> None:
        """Fetch the last 10 match IDs and detailed data for the latest match."""
        if not self._puuid:
            _LOGGER.warning("No PUUID available, cannot fetch match history")
            return
            
        # Get regional cluster for match API
        regional_cluster = REGION_CLUSTERS.get(self._region, "americas")
        
        # Get last 10 match IDs
        url = f"https://{regional_cluster}.api.riotgames.com/lol/match/v5/matches/by-puuid/{self._puuid}/ids?start=0&count=10"
        headers = self._get_headers()
        timeout = ClientTimeout(total=10)
        
        _LOGGER.info("Fetching match history for PUUID %s", self._puuid[:8] + "...")
        
        try:
            async with self._session.get(url, headers=headers, timeout=timeout) as response:
                if response.status == 200:
                    match_ids = await response.json()
                    self._match_history = match_ids
                    _LOGGER.info("Retrieved %d match IDs: %s", len(match_ids), match_ids[:3] if match_ids else [])
                    
                    # If we have matches, fetch detailed data for the latest one
                    if match_ids and (not self._last_match_id or match_ids[0] != self._last_match_id):
                        latest_match_id = match_ids[0]
                        _LOGGER.info("Fetching detailed data for latest match: %s", latest_match_id)
                        
                        # Fetch detailed match data
                        match_data = await self._fetch_match_details_full(latest_match_id, regional_cluster)
                        if match_data:
                            self._last_match_data = match_data
                            self._last_match_id = latest_match_id
                            _LOGGER.info("Updated latest match data for match: %s", latest_match_id)
                        
                elif response.status == 404:
                    _LOGGER.warning("No match history found for player")
                    self._match_history = []
                elif response.status == 429:
                    _LOGGER.warning("Rate limit exceeded for match history")
                else:
                    _LOGGER.warning("Error fetching match history: %s", response.status)
                    
        except ClientResponseError as err:
            _LOGGER.warning("HTTP error fetching match history: %s", err)
        except Exception as err:
            _LOGGER.warning("Unexpected error fetching match history: %s", err)

    async def _fetch_match_details_full(self, match_id: str, regional_cluster: str) -> Optional[Dict[str, Any]]:
        """Fetch full detailed match information including all participant data."""
        url = f"https://{regional_cluster}.api.riotgames.com/lol/match/v5/matches/{match_id}"
        headers = self._get_headers()
        timeout = ClientTimeout(total=10)
        
        try:
            async with self._session.get(url, headers=headers, timeout=timeout) as response:
                if response.status == 200:
                    match_data = await response.json()
                    return self._process_full_match_data(match_data)
                else:
                    _LOGGER.warning("Error fetching full match details for %s: %s", match_id, response.status)
                    return None
                    
        except ClientResponseError as err:
            _LOGGER.warning("HTTP error fetching full match details: %s", err)
            return None
        except Exception as err:
            _LOGGER.warning("Unexpected error fetching full match details: %s", err)
            return None

    def _process_full_match_data(self, match_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process full match data including all available information."""
        # Find player's participant data
        participant = None
        for p in match_data["info"]["participants"]:
            if p.get("puuid") == self._puuid:
                participant = p
                break
        
        if not participant:
            _LOGGER.error("Player not found in match data")
            return {}
        
        # Extract comprehensive match information
        info = match_data.get("info", {})
        metadata = match_data.get("metadata", {})
        
        # Basic stats
        kills = participant.get("kills", 0)
        deaths = participant.get("deaths", 0)
        assists = participant.get("assists", 0)
        kda = (kills + assists) / max(deaths, 1)
        
        # Additional participant stats
        champion_name = participant.get("championName", "Unknown")
        champion_level = participant.get("champLevel", 0)
        win = participant.get("win", False)
        
        # Game information
        game_mode = info.get("gameMode", "Unknown")
        game_type = info.get("gameType", "Unknown")
        queue_id = info.get("queueId", 0)
        game_duration = info.get("gameDuration", 0)
        game_start_timestamp = info.get("gameStartTimestamp", 0)
        game_end_timestamp = info.get("gameEndTimestamp", 0)
        
        # Performance stats
        total_damage_dealt = participant.get("totalDamageDealtToChampions", 0)
        total_damage_taken = participant.get("totalDamageTaken", 0)
        gold_earned = participant.get("goldEarned", 0)
        cs_total = participant.get("totalMinionsKilled", 0) + participant.get("neutralMinionsKilled", 0)
        vision_score = participant.get("visionScore", 0)
        
        # Items (0-6 slots)
        items = []
        for i in range(7):  # Items 0-6
            item_id = participant.get(f"item{i}", 0)
            if item_id > 0:
                items.append(item_id)
        
        return {
            "match_id": metadata.get("matchId", "Unknown"),
            "game_start_timestamp": game_start_timestamp,
            "game_end_timestamp": game_end_timestamp,
            "game_duration": game_duration,
            "game_mode": game_mode,
            "game_type": game_type,
            "queue_id": queue_id,
            "champion": champion_name,
            "champion_level": champion_level,
            "kills": kills,
            "deaths": deaths,
            "assists": assists,
            "kda": round(kda, 2),
            "win": win,
            "total_damage_dealt": total_damage_dealt,
            "total_damage_taken": total_damage_taken,
            "gold_earned": gold_earned,
            "cs_total": cs_total,
            "vision_score": vision_score,
            "items": items,
            "participant_data": participant,  # Full participant data for advanced use
            "all_participants": info.get("participants", []),  # All players in the match
        }

    async def _fetch_summoner_level(self) -> int:
        """Fetch summoner account level (not in-game champion level) using PUUID."""
        if not self._puuid:
            _LOGGER.warning("No PUUID available, cannot fetch summoner level")
            return 0
            
        url = f"https://{self._region}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{self._puuid}"
        headers = self._get_headers()
        timeout = ClientTimeout(total=10)
        
        _LOGGER.info("Fetching summoner level for PUUID %s", self._puuid[:8] + "...")
        
        try:
            async with self._session.get(url, headers=headers, timeout=timeout) as response:
                if response.status == 200:
                    data = await response.json()
                    level = data.get("summonerLevel", 0)
                    _LOGGER.info("Successfully fetched summoner level: %d", level)
                    return level
                else:
                    _LOGGER.warning("Error fetching summoner level: %s", response.status)
                    return 0
                    
        except Exception as err:
            _LOGGER.warning("Error fetching summoner level: %s", err)
            return 0

    def _build_comprehensive_data(self, current_game_data: Optional[Dict[str, Any]], ranked_stats: Dict[str, Any], summoner_level: int, player_status: str = "unknown") -> Dict[str, Any]:
        """Build comprehensive data combining current game, latest match, and other stats."""
        # Start with base data
        data = {
            "last_updated": datetime.now().isoformat(),
            "summoner_level": summoner_level,
        }
        
        # Add ranked stats safely
        if ranked_stats:
            data.update(ranked_stats)
        else:
            data["rank"] = "Unknown"
        
        # Determine the appropriate state based on player status and current game data
        if current_game_data:
            _LOGGER.info("Player is in League of Legends game")
            data.update(current_game_data)
            # The state is already set correctly in current_game_data, don't override it
            
            # Add latest match stats for the stat entities (keeping current game stats as primary)
            if self._last_match_data:
                latest_match = self._last_match_data
                data.update({
                    "latest_match_id": latest_match.get("match_id"),
                    "latest_champion": latest_match.get("champion"),
                    "latest_kills": latest_match.get("kills", 0),
                    "latest_deaths": latest_match.get("deaths", 0),
                    "latest_assists": latest_match.get("assists", 0),
                    "latest_kda": latest_match.get("kda", 0.0),
                    "latest_win": latest_match.get("win"),
                    "latest_match_data": latest_match,
                })
        else:
            # Not in League game - use player status to determine state
            _LOGGER.debug("Player is not in League game - status: %s", player_status)
            
            # Map player status to our honest game states
            state_map = {
                "recently_played": GAME_STATES.get("recently_played", "Played Recently"),
                "touching_grass": GAME_STATES.get("touching_grass", "Touching Grass"),
                "in_game": GAME_STATES.get("in_game", "In Game"),  # Backup mapping
            }
            
            # Set the state based on our honest detection
            data["state"] = state_map.get(player_status, GAME_STATES.get("touching_grass", "Touching Grass"))
            
            if self._last_match_data:
                latest_match = self._last_match_data
                data.update({
                    "game_mode": latest_match.get("game_mode"),
                    "queue_type": latest_match.get("queue_type"),  # Fixed: was queue_id
                    "champion": latest_match.get("champion", "Unknown"),
                    "match_id": latest_match.get("match_id"),
                    "kills": latest_match.get("kills", 0),
                    "deaths": latest_match.get("deaths", 0),
                    "assists": latest_match.get("assists", 0),
                    "kda": latest_match.get("kda", 0.0),
                    "latest_match_id": latest_match.get("match_id"),
                    "latest_champion": latest_match.get("champion"),
                    "latest_kills": latest_match.get("kills", 0),
                    "latest_deaths": latest_match.get("deaths", 0),
                    "latest_assists": latest_match.get("assists", 0),
                    "latest_kda": latest_match.get("kda", 0.0),
                    "latest_win": latest_match.get("win"),
                    "latest_match_data": latest_match,
                })
            else:
                # No match data available - definitely touching grass
                data.update({
                    "game_mode": None,
                    "queue_type": None,
                    "champion": "No recent matches",
                    "match_id": None,
                    "kills": 0,
                    "deaths": 0,
                    "assists": 0,
                    "kda": 0.0,
                    "latest_match_id": None,
                    "latest_champion": None,
                    "latest_kills": 0,
                    "latest_deaths": 0,
                    "latest_assists": 0,
                    "latest_kda": 0.0,
                    "latest_win": None,
                    "latest_match_data": None,
                })
        
        return data

    @property
    def match_history(self) -> Optional[list]:
        """Return the list of last 10 match IDs."""
        return self._match_history

    @property
    def latest_match_data(self) -> Optional[Dict[str, Any]]:
        """Return detailed data for the latest match."""
        return self._last_match_data

    async def async_will_remove_from_hass(self):
        """Clean up when removed from Home Assistant."""
        if hasattr(self, '_session') and self._session and not self._session.closed:
            await self._session.close()
