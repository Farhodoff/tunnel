from typing import Dict

def sanitize_metric_labels(labels: Dict[str, str]) -> Dict[str, str]:
    """Sanitize Prometheus label keys and values to prevent injection."""
    sanitized = {}
    for k, v in labels.items():
        clean_key = "".join(c for c in k if c.isalnum() or c == "_")
        clean_val = str(v).replace('"', '\\"').replace("\n", "")
        if clean_key:
            sanitized[clean_key] = clean_val
    return sanitized
