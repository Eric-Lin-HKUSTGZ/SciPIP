import os

# API Configuration
API_HOST = os.getenv("SCIPIP_API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("SCIPIP_API_PORT", "8888"))
API_TITLE = "SciPIP API"
API_DESCRIPTION = "API service for generating scientific paper ideas using SciPIP"
API_VERSION = "1.0.0"

# HTTP Endpoints Configuration
GENERATE_ENDPOINT = "/generate"
HEALTH_ENDPOINT = "/health"

# File Paths
CONFIG_PATH = "./configs/datasets.yaml"
EXAMPLE_PATH = "./assets/data/example.json"

# Workflow Parameters
USE_INSPIRATION = True
BRAINSTORM_MODE = "mode_c"

# Logging Configuration
LOG_LEVEL = os.getenv("SCIPIP_LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Error Handling
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# CORS Configuration
ALLOWED_ORIGINS = os.getenv("SCIPIP_ALLOWED_ORIGINS", "*").split(",")  # Configure appropriately for production

# Request Timeout Configuration
REQUEST_TIMEOUT = 480  # seconds (8 minutes) for long-running operations

