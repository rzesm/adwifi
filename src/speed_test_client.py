import json
import subprocess


async def test_speed() -> tuple[float, float, float]:    
    output_json = subprocess.run(
        f"/usr/bin/speedtest-cli --json --secure", 
        shell=True, text=True, capture_output=True
    ).stdout
    return json.loads(output_json)