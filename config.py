# Configuration for the Kaspi scraper project

# Proxy rotation list. Example format: ["http://user:pass@host:port", "http://..."]
# Leave empty for no proxy during testing.
PROXIES = []

# Default headers (User-Agent will be randomized normally)
TIMEOUT = 20  # seconds per request
MAX_WORKERS = 5  # concurrency for async extensions (not used in simple sync version)
CHUNK_SIZE = 5000  # rows per output file

# Matching thresholds
FUZZY_THRESHOLD = 70  # percent; below this we consider trying next candidate
SECONDARY_THRESHOLD = 40  # percent used in the user's description for GPT fallback

# Optional OpenAI (GPT) settings - leave empty if not using
OPENAI_API_KEY = ""

# Request delay (randomized between MIN_DELAY and MAX_DELAY seconds)
MIN_DELAY = 0.6
MAX_DELAY = 1.8

# Logging
LOG_LEVEL = "INFO"