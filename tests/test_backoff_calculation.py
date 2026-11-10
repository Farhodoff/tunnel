import pytest

def calculate_backoff(attempt: int, base: float = 1.0, max_backoff: float = 30.0) -> float:
    return min(base * (2 ** attempt), max_backoff)

def test_exponential_backoff_progression():
    assert calculate_backoff(0) == 1.0
    assert calculate_backoff(1) == 2.0
    assert calculate_backoff(2) == 4.0
    assert calculate_backoff(3) == 8.0
    assert calculate_backoff(4) == 16.0
    assert calculate_backoff(5) == 30.0  # capped at max_backoff
    assert calculate_backoff(10) == 30.0
