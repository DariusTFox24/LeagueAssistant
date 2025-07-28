"""Data update coordinator for Riot LoL integration."""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from urllib.parse import quote

from aiohttp import ClientSession, ClientResponseError, ClientTimeout
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import REGION_CLUSTERS, GAME_STATES

_LOGGER = logging.getLogger(__name__)


class RiotLoLDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Riot LoL data."""

    def __init__(
        self,
        hass: HomeAssistant,
        api_key: str,
        game_name: str,
        tag_line: str,
        region: str,
        session: ClientSession = None,
        update_interval: timedelta = timedelta(minutes=5),
        puuid: Optional[str] = None,
    ):
        """Initialize the coordinator."""
        self._api_key = api_key
        self._game_name = game_name
        self._tag_line = tag_line
        self._region = region
        self._session = session or async_get_clientsession(hass)
        self._puuid: Optional[str] = puuid  # Use pre-validated PUUID if available
        self._summoner_id: Optional[str] = None
        self._last_match_id: Optional[str] = None
        self._last_match_data: Optional[Dict[str, Any]] = None
        self._match_history: Optional[list] = None
        self._consecutive_errors = 0
        self._max_errors = 5
        
        riot_id = f"{game_name}#{tag_line}" if tag_line else game_name
        
        super().__init__(
            hass,
            _LOGGER,
            name=f"Riot LoL Data for {riot_id}",
            update_interval=update_interval,
        )
        
        if self._puuid:
            _LOGGER.info(f"Using pre-validated PUUID for {riot_id}: {self._puuid[:8]}...")
        else:
            _LOGGER.info(f"No pre-validated PUUID, will fetch account info for {riot_id}")

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from Riot API."""
        try:
            # Initialize PUUID if not set
            if not self._puuid:
                try:
                    await self._fetch_account_info()
                except UpdateFailed as err:
                    _LOGGER.error("Failed to fetch account info: %s", err)
                    raise
            
            # Fetch current game status (requires summoner ID)
            try:
                current_game = await self._fetch_current_game()
                if current_game:
                    return await self._process_current_game(current_game)
            except Exception as err:
                _LOGGER.warning("Error checking current game, continuing: %s", err)
            
            # If not in game, fetch latest match data (uses PUUID)
            try:
                latest_match_data = await self._fetch_latest_match_data()
                if latest_match_data:
                    return latest_match_data
            except Exception as err:
                _LOGGER.warning("Error fetching match data, continuing: %s", err)
            
            # Fetch match history for the latest match sensor
            try:
                await self._fetch_match_history()
            except Exception as err:
                _LOGGER.warning("Error fetching match history: %s", err)
            
            # Fetch ranked stats as fallback (uses PUUID - more reliable)
            try:
                ranked_stats = await self._fetch_ranked_stats()
            except Exception as err:
                _LOGGER.warning("Error fetching ranked stats: %s", err)
                ranked_stats = {"rank": "Unknown"}
            
            self._consecutive_errors = 0  # Reset error counter on success
            
            # Return comprehensive default data when not in game or no recent matches
            return {
                "state": GAME_STATES.get("online", "Online"),
                "last_updated": datetime.now().isoformat(),
                "game_mode": None,
                "queue_type": None,
                "champion": "Not in game",
                "match_id": None,
                "kills": 0,
                "deaths": 0,
                "assists": 0,
                "kda": 0.0,
                "match_history_count": len(self._match_history) if self._match_history else 0,
                "latest_match_available": self._last_match_data is not None,
                **ranked_stats,
            }
            
        except UpdateFailed:
            # Re-raise UpdateFailed exceptions (these are expected)
            raise
        except Exception as err:
            self._consecutive_errors += 1
            _LOGGER.error("Unexpected error in coordinator update: %s", err, exc_info=True)
            
            if self._consecutive_errors >= self._max_errors:
                _LOGGER.error(
                    "Too many consecutive errors (%d), marking as offline: %s",
                    self._consecutive_errors,
                    err
                )
                return {
                    "state": GAME_STATES["offline"],
                    "last_updated": datetime.now().isoformat(),
                    "error": str(err),
                }
            
            raise UpdateFailed(f"Error communicating with Riot API: {err}")

    async def _fetch_account_info(self) -> None:
        """Fetch account info using Riot ID."""
        regional_cluster = REGION_CLUSTERS.get(self._region, "americas")
        
        encoded_game_name = quote(self._game_name, safe='')
        encoded_tag_line = quote(self._tag_line, safe='') if self._tag_line else ""
        
        url = f"https://{regional_cluster}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{encoded_game_name}/{encoded_tag_line}"
        headers = {"X-Riot-Token": self._api_key}
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
        headers = {"X-Riot-Token": self._api_key}
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
                    raise UpdateFailed(f"Summoner not found for PUUID {self._puuid[:8]}... in region {self._region}")
                elif response.status == 429:
                    raise UpdateFailed("Rate limit exceeded")
                elif response.status == 401:
                    raise UpdateFailed("Invalid API key for summoner lookup")
                else:
                    raise UpdateFailed(f"API error fetching summoner: {response.status}")
                    
        except ClientResponseError as err:
            raise UpdateFailed(f"HTTP error fetching summoner info: {err}")
        except KeyError as err:
            raise UpdateFailed(f"Missing expected field in summoner response: {err}")
        except Exception as err:
            raise UpdateFailed(f"Unexpected error fetching summoner info: {err}")

    async def _fetch_current_game(self) -> Optional[Dict[str, Any]]:
        """Check if player is currently in a game."""
        # Try to get summoner ID if we don't have it
        if not self._summoner_id:
            try:
                await self._fetch_summoner_info()
            except UpdateFailed as err:
                _LOGGER.warning("Cannot fetch summoner ID for current game check: %s", err)
                return None
            
        if not self._summoner_id:
            _LOGGER.info("No summoner ID available, skipping current game check")
            return None
            
        url = f"https://{self._region}.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{self._summoner_id}"
        headers = {"X-Riot-Token": self._api_key}
        timeout = ClientTimeout(total=10)
        
        try:
            async with self._session.get(url, headers=headers, timeout=timeout) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 404:
                    # Not in game
                    return None
                elif response.status == 429:
                    _LOGGER.warning("Rate limit exceeded for current game check")
                    return None
                else:
                    _LOGGER.warning("Error checking current game: %s", response.status)
                    return None
                    
        except ClientResponseError as err:
            _LOGGER.warning("HTTP error checking current game: %s", err)
            return None
        except Exception as err:
            _LOGGER.warning("Unexpected error checking current game: %s", err)
            return None

    async def _process_current_game(self, game_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process current game data."""
        try:
            # Find the player in the participants
            participant = None
            for p in game_data.get("participants", []):
                if p.get("puuid") == self._puuid or p.get("summonerId") == self._summoner_id:
                    participant = p
                    break
            
            if not participant:
                # Try to find by summoner name as fallback
                for p in game_data.get("participants", []):
                    if p.get("summonerName", "").lower() == self._game_name.lower():
                        participant = p
                        break
            
            if not participant:
                raise UpdateFailed("Player not found in current game data")
            
            return {
                "state": GAME_STATES.get("in_game", "In Game"),
                "game_mode": game_data.get("gameMode", "Unknown"),
                "queue_type": game_data.get("gameQueueConfigId"),
                "champion": participant.get("championName", "Unknown"),
                "game_start_time": game_data.get("gameStartTime", 0),
                "game_length": game_data.get("gameLength", 0),
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
        headers = {"X-Riot-Token": self._api_key}
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
        headers = {"X-Riot-Token": self._api_key}
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
        headers = {"X-Riot-Token": self._api_key}
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
                            "tier": solo_queue.get("tier", "Unranked"),
                            "division": solo_queue.get("rank", ""),
                            "lp": solo_queue.get("leaguePoints", 0),
                            "wins": wins,
                            "losses": losses,
                            "win_rate": round(win_rate, 1),
                        }
                    else:
                        _LOGGER.info("No RANKED_SOLO_5x5 queue found in response")
                        return {"rank": "Unranked"}
                elif response.status == 404:
                    _LOGGER.info("No ranked data found for player (likely unranked)")
                    return {"rank": "Unranked"}
                else:
                    _LOGGER.warning("Error fetching ranked stats: %s", response.status)
                    return {"rank": "Unknown"}
                    
        except ClientResponseError as err:
            _LOGGER.warning("HTTP error fetching ranked stats: %s", err)
            
        return {"rank": "Unknown"}

    async def _fetch_match_history(self) -> None:
        """Fetch the last 10 match IDs and detailed data for the latest match."""
        if not self._puuid:
            _LOGGER.warning("No PUUID available, cannot fetch match history")
            return
            
        # Get regional cluster for match API
        regional_cluster = REGION_CLUSTERS.get(self._region, "americas")
        
        # Get last 10 match IDs
        url = f"https://{regional_cluster}.api.riotgames.com/lol/match/v5/matches/by-puuid/{self._puuid}/ids?start=0&count=10"
        headers = {"X-Riot-Token": self._api_key}
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
        headers = {"X-Riot-Token": self._api_key}
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
