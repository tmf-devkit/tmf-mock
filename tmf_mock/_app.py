"""
ASGI entry point — loaded by uvicorn via `tmf_mock._app:app`.
Reads config from environment variables set by the CLI.
"""
import os

apis_env = os.environ.get("TMF_MOCK_APIS", "638,639,641")
seed_env = os.environ.get("TMF_MOCK_SEED", "1")
base_url = os.environ.get("TMF_MOCK_BASE_URL", "http://localhost:8000")

api_list = [int(a.strip()) for a in apis_env.split(",") if a.strip().isdigit()]
seed = seed_env != "0"

from tmf_mock.server import create_app

app = create_app(apis=api_list, seed=seed, base_url=base_url)
