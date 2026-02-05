# coremind/infrastructure/smart_home/device_registry.py

import yaml
from pathlib import Path

_REGISTRY_PATH = Path(__file__).parent / "devices.yaml"

with open(_REGISTRY_PATH, "r") as f:
    _DEVICES = yaml.safe_load(f)


def resolve_device(room: str, name: str) -> dict:
    try:
        return _DEVICES[room][name]
    except KeyError:
        raise KeyError(f"No device registered for {room}.{name}")
