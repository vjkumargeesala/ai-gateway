import os
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()


def _parse_api_keys(raw: str) -> dict[str, str]:
    """Parse 'key1:user1,key2:user2' into {key1: user1, key2: user2}."""
    result = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if not pair:
            continue
        if ":" not in pair:
            raise ValueError(f"Invalid API_KEYS entry: '{pair}' (expected 'key:user')")
        key, user = pair.split(":", 1)
        result[key.strip()] = user.strip()
    return result


class Config(BaseModel):
    app_env: str = os.getenv("APP_ENV", "development")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    api_keys: dict[str, str] = _parse_api_keys(os.getenv("API_KEYS", ""))
    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "100"))
    llm_fail_rate: float = float(os.getenv("LLM_FAIL_RATE", "0.0"))
    llm_latency_ms: int = int(os.getenv("LLM_LATENCY_MS", "200"))


config = Config()

if not config.api_keys:
    raise ValueError("API_KEYS environment variable is not set or empty")