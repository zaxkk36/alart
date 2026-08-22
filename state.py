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


def already_alerted(state: dict, symbol: str, candle_time_iso: str) -> bool:
    return state.get(symbol) == candle_time_iso


def mark_alerted(state: dict, symbol: str, candle_time_iso: str) -> None:
    state[symbol] = candle_time_iso
