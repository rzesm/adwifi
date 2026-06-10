import json
import subprocess


class SpeedTestError(RuntimeError):
    def __init__(self, message: str):
        super().__init__(message)

async def test_speed() -> tuple[float, float, float] | None:    
    try:
        output_json = subprocess.run(
            f"/usr/bin/speedtest-cli --json --secure", 
            shell=True, text=True, capture_output=True
        ).stdout
        return json.loads(output_json)
    except Exception:
        raise SpeedTestError("Failed to query connection data")