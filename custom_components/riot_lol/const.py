"""Constants for the Riot LoL integration."""

DOMAIN = "riot_lol"

# Configuration constants
CONF_API_KEY = "api_key"
CONF_GAME_NAME = "game_name"
CONF_TAG_LINE = "tag_line"
CONF_REGION = "region"
CONF_RIOT_ID = "riot_id"

# Default values
DEFAULT_REGION = "eun1"  # Changed to EUNE for testing
DEFAULT_SCAN_INTERVAL = 60   # 1 minute for more frequent updates
MIN_SCAN_INTERVAL = 60       # 1 minute
MAX_SCAN_INTERVAL = 3600     # 1 hour

# API endpoints and regions (Updated 2025)
REGION_CLUSTERS = {
    # Americas
    "na1": "americas",
    "br1": "americas", 
    "la1": "americas",
    "la2": "americas",
    # Europe
    "euw1": "europe",
    "eun1": "europe",  # Europe Nordic & East (EUNE)
    "tr1": "europe",   # Turkey
    "ru1": "europe",   # Russia (fixed from "ru" to "ru1")
    # Asia
    "kr": "asia",
    "jp1": "asia",
    # SEA (Southeast Asia)
    "oc1": "sea",      # Oceania
    "ph2": "sea",      # Philippines
    "sg2": "sea",      # Singapore
    "th2": "sea",      # Thailand
    "tw2": "sea",      # Taiwan
    "vn2": "sea"       # Vietnam
}

PLATFORM_REGIONS = list(REGION_CLUSTERS.keys())

# Game states
GAME_STATES = {
    "in_game": "In Game",
    "recently_played": "Played Recently",
    "touching_grass": "Touching Grass",
    "unknown": "Unknown"
}

# Sensor types
SENSOR_TYPES = [
    "game_state",
    "kills",
    "deaths", 
    "assists",
    "kda",
    "champion",
    "rank"
]
