from coremind.agents.nemesis.tools.smart_home_control import SmartHomeControlTool 
def test_smart_home_tool():
    tool = SmartHomeControlTool()

    command = {
        "device_id": "living_room_light",
        "action": "switch_on"
    }

    result = tool.run(command)

    assert result["ok"] is True
    assert result["terminal"] is True
    assert result["device_id"] == "living_room_light"
    assert result["action"] == "switch_on"

    print("TEST PASSED:", result)


if __name__ == "__main__":
    test_smart_home_tool()
