import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Required Configuration
API_ID = int(os.getenv('API_ID', '0'))
API_HASH = os.getenv('API_HASH', '')
BOT_TOKEN = os.getenv('BOT_TOKEN', '')
OWNER = int(os.getenv('OWNER', '0'))
CREDIT = os.getenv('CREDIT', 'Bot Owner')

# User Lists
AUTH_USERS = []
TOTAL_USERS = []

# File paths
cookies_file_path = "youtube_cookies.txt"

# API configurations
api_url = ""
api_token = ""

# Token variables (these were missing!)
token_cp = ""
adda_token = ""

# Photo URLs for bot interface
photologo = "https://envs.sh/GVI.jpg"
photoyt = "https://envs.sh/GVI.jpg"
photocp = "https://envs.sh/GVI.jpg"
photozip = "https://envs.sh/GVI.jpg"
