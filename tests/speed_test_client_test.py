import json
import subprocess
from unittest.mock import patch, MagicMock
import pytest

from adwifi.speed_test_client import run_speed_test

@pytest.mark.asyncio
async def test_run_speed_test():
    fake_speedtest_data = {
        "download": 125.50,
        "upload": 45.20,
        "ping": 14.1
    }
    
    mock_process = MagicMock(spec=subprocess.CompletedProcess)
    mock_process.stdout = json.dumps(fake_speedtest_data)

    with patch("adwifi.speed_test_client.subprocess.run", return_value=mock_process) as mock_run:
        
        result = await run_speed_test()
        
        assert isinstance(result, dict)
        assert "download" in result
        assert "upload" in result
        assert "ping" in result
        assert isinstance(result["download"], float)
        assert result["download"] == 125.50

        mock_run.assert_called_once_with(
            "/usr/bin/speedtest-cli --json --secure",
            shell=True, 
            text=True, 
            capture_output=True
        )