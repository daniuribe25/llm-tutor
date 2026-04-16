from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

MODEL = os.getenv("OLLAMA_MODEL", "gemma4:31b-cloud")
