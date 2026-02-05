# tools/smart_home_control.py

from typing import Dict, Any
import logging

log = logging.getLogger(__name__)


class SmartHomeControlTool:
    """
    Executes a single smart home command.
    This tool is TERMINAL by design.
    """

    name = "smart_home_control"
    description = "Control smart home devices by sending commands to switch power on/off or toggle."
    args_schema = {
        "device_id": {
            "type": "string",
            "required": True,
            "description": "The unique identifier of the smart home device to control.",
        },
        "action": {
            "type": "string",
            "required": True,
            "description": "The action to perform: 'switch_on', 'switch_off', or 'toggle'.",
        },
    }
    domain = "smart_home"
    terminal = True

    def run(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """
        Expected command:
        {
            "device_id": "living_room_light",
            "action": "switch_on"
        }
        """

        device_id = command.get("device_id")
        action = command.get("action")

        if not device_id or not action:
            return {
                "ok": False,
                "error": "device_id and action are required",
                "terminal": True
            }

        log.info("SMART_HOME | Device=%s Action=%s", device_id, action)

        # ---- MOCK EXECUTION LAYER ----
        # Replace this with ESP32 / MQTT / HomeAssistant later
        result = self._execute(device_id, action)

        return {
            "ok": True,
            "device_id": device_id,
            "action": action,
            "result": result,
            "terminal": True
        }

    def _execute(self, device_id: str, action: str) -> str:
        # Stubbed hardware interaction
        if action == "switch_on":
            return f"{device_id} turned ON"
        elif action == "switch_off":
            return f"{device_id} turned OFF"
        elif action == "toggle":
            return f"{device_id} toggled"
        else:
            raise ValueError(f"Unsupported action: {action}")
