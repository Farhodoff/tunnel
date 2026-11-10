import json
import os
from typing import Dict, Any

def load_client_config(file_path: str) -> Dict[str, Any]:
    """Load configuration from JSON or key-value file."""
    if not os.path.exists(file_path):
        return {}
    
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            # Fallback to key=value parsing
            f.seek(0)
            config = {}
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    config[k.strip()] = v.strip()
            return config
