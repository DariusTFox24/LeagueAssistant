"""Constants for the Riot LoL integration."""

DOMAIN = "riot_lol"

# Configuration constants
CONF_API_KEY = "api_key"
CONF_GAME_NAME = "game_name"
CONF_TAG_LINE = "tag_line"
CONF_REGION = "region"
CONF_RIOT_ID = "riot_id"

# Default values
DEFAULT_REGION = "euw1"
DEFAULT_SCAN_INTERVAL = 300  # 5 minutes
MIN_SCAN_INTERVAL = 60       # 1 minute
MAX_SCAN_INTERVAL = 3600     # 1 hour

# API endpoints and regions
REGION_CLUSTERS = {
    "na1": "americas",
    "br1": "americas", 
    "la1": "americas",
    "la2": "americas",
    "euw1": "europe",
    "eun1": "europe",
    "tr1": "europe",
    "ru": "europe",
    "kr": "asia",
    "jp1": "asia",
    "oc1": "sea",
    "ph2": "sea",
    "sg2": "sea",
    "th2": "sea",
    "tw2": "sea",
    "vn2": "sea"
}

PLATFORM_REGIONS = list(REGION_CLUSTERS.keys())

# Game states
GAME_STATES = {
    "in_game": "In Game",
    "in_queue": "In Queue", 
    "in_champ_select": "Champion Select",
    "offline": "Offline",
    "online": "Online",
    "away": "Away",
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
