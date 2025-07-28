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
    ):
        """Initialize the coordinator."""
        self._api_key = api_key
        self._game_name = game_name
        self._tag_line = tag_line
        self._region = region
        self._session = session or async_get_clientsession(hass)
        self._puuid: Optional[str] = None
        self._summoner_id: Optional[str] = None
        self._last_match_id: Optional[str] = None
        self._consecutive_errors = 0
        self._max_errors = 5
        
        riot_id = f"{game_name}#{tag_line}" if tag_line else game_name
        
        super().__init__(
            hass,
            _LOGGER,
            name=f"Riot LoL Data for {riot_id}",
            update_interval=update_interval,
        )

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from Riot API."""
        try:
            # Initialize PUUID if not set
            if not self._puuid:
                await self._fetch_account_info()
            
            # Fetch current game status
            current_game = await self._fetch_current_game()
            if current_game:
                return await self._process_current_game(current_game)
            
            # If not in game, fetch latest match data
            latest_match_data = await self._fetch_latest_match_data()
            if latest_match_data:
                return latest_match_data
            
            # Fetch ranked stats as fallback
            ranked_stats = await self._fetch_ranked_stats()
            
            self._consecutive_errors = 0  # Reset error counter on success
            return {
                "state": GAME_STATES["online"],
                "last_updated": datetime.now().isoformat(),
                **ranked_stats,
            }
            
        except Exception as err:
            self._consecutive_errors += 1
            
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
        
        try:
            async with self._session.get(url, headers=headers, timeout=timeout) as response:
                if response.status == 200:
                    data = await response.json()
                    self._puuid = data["puuid"]
                    _LOGGER.debug("Retrieved PUUID: %s", self._puuid[:8] + "...")
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

    async def _fetch_summoner_info(self) -> None:
        """Fetch summoner info using PUUID."""
        if not self._puuid:
            await self._fetch_account_info()
            
        url = f"https://{self._region}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{self._puuid}"
        headers = {"X-Riot-Token": self._api_key}
        timeout = ClientTimeout(total=10)
        
        try:
            async with self._session.get(url, headers=headers, timeout=timeout) as response:
                if response.status == 200:
                    data = await response.json()
                    self._summoner_id = data["id"]
                    _LOGGER.debug("Retrieved summoner ID: %s", self._summoner_id)
                elif response.status == 429:
                    raise UpdateFailed("Rate limit exceeded")
                else:
                    raise UpdateFailed(f"API error fetching summoner: {response.status}")
                    
        except ClientResponseError as err:
            raise UpdateFailed(f"HTTP error fetching summoner info: {err}")

    async def _fetch_current_game(self) -> Optional[Dict[str, Any]]:
        """Check if player is currently in a game."""
        if not self._puuid:
            return None
            
        url = f"https://{self._region}.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{self._puuid}"
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

    async def _process_current_game(self, game_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process current game data."""
        # Find the player in the participants
        participant = None
        for p in game_data.get("participants", []):
            if p.get("puuid") == self._puuid:
                participant = p
                break
        
        if not participant:
            raise UpdateFailed("Player not found in current game data")
        
        return {
            "state": GAME_STATES["in_game"],
            "game_mode": game_data.get("gameMode", "Unknown"),
            "queue_type": game_data.get("gameQueueConfigId"),
            "champion": participant.get("championName", "Unknown"),
            "game_start_time": game_data.get("gameStartTime", 0),
            "game_length": game_data.get("gameLength", 0),
            "last_updated": datetime.now().isoformat(),
            "match_id": str(game_data.get("gameId", "")),
        }

    async def _fetch_latest_match_data(self) -> Optional[Dict[str, Any]]:
        """Fetch data from the latest match."""
        if not self._puuid:
            return None
            
        # Get regional cluster for match API
        regional_cluster = REGION_CLUSTERS.get(self._region, "americas")
        if self._region in ["kr", "jp1"]:
            regional_cluster = "asia"
        elif self._region in ["oc1", "ph2", "sg2", "th2", "tw2", "vn2"]:
            regional_cluster = "sea"
        
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
        
        return {
            "state": GAME_STATES["online"],
            "kills": participant.get("kills", 0),
            "deaths": participant.get("deaths", 0),
            "assists": participant.get("assists", 0),
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
        """Fetch ranked statistics."""
        if not self._summoner_id:
            await self._fetch_summoner_info()
            
        if not self._summoner_id:
            return {}
            
        url = f"https://{self._region}.api.riotgames.com/lol/league/v4/entries/by-summoner/{self._summoner_id}"
        headers = {"X-Riot-Token": self._api_key}
        timeout = ClientTimeout(total=10)
        
        try:
            async with self._session.get(url, headers=headers, timeout=timeout) as response:
                if response.status != 200:
                    _LOGGER.warning("Error fetching ranked stats: %s", response.status)
                    return {}
                    
                ranked_data = await response.json()
                
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
                    
        except ClientResponseError as err:
            _LOGGER.warning("HTTP error fetching ranked stats: %s", err)
            
        return {"rank": "Unranked"}

        async with self._session.get(url, headers=headers) as response:
            if response.status != 200:
                raise UpdateFailed(f"Failed to fetch match details: {response.status}")
            data = await response.json()
            return data

    async def _async_update_data(self):
        if self._puuid is None:
            await self._fetch_summoner_info()

        latest_match_id = await self._fetch_latest_match()
        if latest_match_id is None:
            return {"state": "No matches found"}

        match_details = await self._fetch_match_details(latest_match_id)
        participants = match_details["info"]["participants"]
        participant_data = next((p for p in participants if p["puuid"] == self._puuid), None)

        if participant_data is None:
            raise UpdateFailed("Player not found in match data")

        return {
            "state": "Win" if participant_data["win"] else "Loss",
            "kills": participant_data["kills"],
            "deaths": participant_data["deaths"],
            "assists": participant_data["assists"],
            "champion": participant_data["championName"],
            "game_mode": match_details["info"]["gameMode"],
            "match_id": latest_match_id,
        }

    async def async_will_remove_from_hass(self):
        await self._session.close()
