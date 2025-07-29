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
DEFAULT_SCAN_INTERVAL = 90   # 1.5 minutes - reduced frequency to avoid rate limits
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

# Queue type mappings (common ones)
QUEUE_TYPES = {
    400: "Normal Draft",
    420: "Ranked Solo/Duo",
    430: "Normal Blind",
    440: "Ranked Flex",
    450: "ARAM",
    900: "URF",
    1020: "One For All",
    1700: "Arena",  # 2v2v2v2 Arena mode
    # Add more as needed
}

# Game mode mappings
GAME_MODES = {
    "CLASSIC": "Summoner's Rift",
    "ARAM": "ARAM",
    "URF": "URF", 
    "ONEFORALL": "One For All",
    "CHERRY": "Arena",  # Arena mode uses CHERRY internally
    "NEXUSBLITZ": "Nexus Blitz",
    "TUTORIAL": "Tutorial",
    "PRACTICETOOL": "Practice Tool",
}

# Map ID to name mappings
MAP_NAMES = {
    1: "Summoner's Rift (Original Summer)",
    2: "Summoner's Rift (Original Autumn)", 
    3: "The Proving Grounds (Tutorial)",
    4: "Twisted Treeline (Original)",
    8: "The Crystal Scar (Dominion)",
    10: "Twisted Treeline (Last)",
    11: "Summoner's Rift",
    12: "Howling Abyss (ARAM)",
    14: "Butcher's Bridge (ARAM)",
    16: "Cosmic Ruins (Dark Star)",
    18: "Valoran City Park (Star Guardian)",
    19: "Substructure 43 (PROJECT)",
    20: "Crash Site (Odyssey)",
    21: "Nexus Blitz",
    22: "Convergence (Teamfight Tactics)",
    30: "Rings of Wrath (Arena)",
}

# Game type mappings  
GAME_TYPES = {
    "CUSTOM_GAME": "Custom Game",
    "MATCHED_GAME": "Matchmade Game",
    "MATCHED": "Matchmade Game",  # Alternative API response
    "TUTORIAL_GAME": "Tutorial"
}

# Champion ID to name mapping (common champions)
CHAMPION_NAMES = {
    1: "Annie", 2: "Olaf", 3: "Galio", 4: "Twisted Fate", 5: "Xin Zhao",
    6: "Urgot", 7: "LeBlanc", 8: "Vladimir", 9: "Fiddlesticks", 10: "Kayle",
    11: "Master Yi", 12: "Alistar", 13: "Ryze", 14: "Sion", 15: "Sivir",
    16: "Soraka", 17: "Teemo", 18: "Tristana", 19: "Warwick", 20: "Nunu & Willump",
    21: "Miss Fortune", 22: "Ashe", 23: "Tryndamere", 24: "Jax", 25: "Morgana",
    26: "Zilean", 27: "Singed", 28: "Evelynn", 29: "Twitch", 30: "Karthus",
    31: "Cho'Gath", 32: "Amumu", 33: "Rammus", 34: "Anivia", 35: "Shaco",
    36: "Dr. Mundo", 37: "Sona", 38: "Kassadin", 39: "Irelia", 40: "Janna",
    41: "Gangplank", 42: "Corki", 43: "Karma", 44: "Taric", 45: "Veigar",
    48: "Trundle", 50: "Swain", 51: "Caitlyn", 53: "Blitzcrank", 54: "Malphite",
    55: "Katarina", 56: "Nocturne", 57: "Maokai", 58: "Renekton", 59: "Jarvan IV",
    60: "Elise", 61: "Orianna", 62: "Wukong", 63: "Brand", 64: "Lee Sin",
    67: "Vayne", 68: "Rumble", 69: "Cassiopeia", 72: "Skarner", 74: "Heimerdinger",
    75: "Nasus", 76: "Nidalee", 77: "Udyr", 78: "Poppy", 79: "Gragas",
    80: "Pantheon", 81: "Ezreal", 82: "Mordekaiser", 83: "Yorick", 84: "Akali",
    85: "Kennen", 86: "Garen", 89: "Leona", 90: "Malzahar", 91: "Talon",
    92: "Riven", 96: "Kog'Maw", 98: "Shen", 99: "Lux", 101: "Xerath",
    102: "Shyvana", 103: "Ahri", 104: "Graves", 105: "Fizz", 106: "Volibear",
    107: "Rengar", 110: "Varus", 111: "Nautilus", 112: "Viktor", 113: "Sejuani",
    114: "Fiora", 115: "Ziggs", 117: "Lulu", 119: "Draven", 120: "Hecarim",
    121: "Kha'Zix", 122: "Darius", 123: "Jayce", 126: "Jayce", 127: "Lissandra",
    131: "Diana", 133: "Quinn", 134: "Syndra", 136: "Aurelion Sol", 141: "Kayn",
    142: "Zoe", 143: "Zyra", 145: "Kai'Sa", 147: "Seraphine", 150: "Gnar",
    154: "Zac", 157: "Yasuo", 161: "Vel'Koz", 163: "Taliyah", 164: "Camille",
    166: "Akshan", 200: "Bel'Veth", 201: "Braum", 202: "Jhin", 203: "Kindred",
    221: "Zeri", 222: "Jinx", 223: "Tahm Kench", 234: "Viego", 235: "Senna",
    236: "Lucian", 238: "Zed", 240: "Kled", 245: "Ekko", 246: "Qiyana",
    254: "Vi", 266: "Aatrox", 267: "Nami", 268: "Azir", 350: "Yuumi",
    360: "Samira", 412: "Thresh", 420: "Illaoi", 421: "Rek'Sai", 427: "Ivern",
    429: "Kalista", 432: "Bard", 516: "Ornn", 517: "Sylas", 518: "Neeko",
    523: "Aphelios", 526: "Rell", 555: "Pyke", 777: "Yone", 875: "Sett",
    876: "Lillia", 887: "Gwen", 888: "Renata Glasc", 895: "Nilah", 897: "K'Sante",
    901: "Smolder", 902: "Ambessa", 950: "Naafiri"
}

# Sensor types
SENSOR_TYPES = [
    "game_state",
    "kills",
    "deaths", 
    "assists",
    "kda",
    "champion",
    "rank",
    "latest_match",
    "level",
    "win_state",
    "win_rate"
]
