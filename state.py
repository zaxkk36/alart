import json
import os
from config import STATE_FILE


def load_state() -> dict:
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def save_state(state: dict) -> None:
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def arm(state: dict, symbol: str, direction: str, break_time_iso: str) -> None:
    """Mark a symbol as 'break detected, waiting for retest'."""
    state[symbol] = {"direction": direction, "break_time": break_time_iso}


def disarm(state: dict, symbol: str) -> None:
    state.pop(symbol, None)


def get_armed(state: dict, symbol: str) -> dict | None:
    return state.get(symbol)
