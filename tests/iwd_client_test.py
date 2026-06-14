import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dbus_next.errors import DBusError

from adwifi.iwd_client import IwdClient, IwdError, IWD_SERVICE


class MockDBusValue:
    def __init__(self, value):
        self.value = value

@pytest.fixture
def mock_bus():
    bus = MagicMock()
    bus.introspect = AsyncMock()
    bus.get_proxy_object = MagicMock()
    return bus

@pytest.fixture
def mock_manager():
    return AsyncMock()

@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop

@pytest.fixture
def client(mock_bus, mock_manager, event_loop):
    return IwdClient(bus=mock_bus, manager=mock_manager, loop=event_loop)


def test_connect_bus(mock_bus, event_loop):
    with patch("adwifi.iwd_client.asyncio.run_coroutine_threadsafe") as mock_run:
        mock_future = MagicMock()
        mock_client_instance = MagicMock(spec=IwdClient)
        mock_run.return_value = mock_future
        mock_future.result.return_value = mock_client_instance

        response = IwdClient.connect_bus(event_loop, mock_bus)
        
        assert response == mock_client_instance
        mock_run.assert_called_once()

def test_handle(client):
    with patch("adwifi.iwd_client.asyncio.run_coroutine_threadsafe") as mock_run:
        mock_request = MagicMock()
        client.handle(mock_request)
        mock_run.assert_called_once_with(mock_request, client._loop)

@pytest.mark.asyncio
async def test_get_adapters(client, mock_manager):
    mock_manager.call_get_managed_objects.return_value = {
        "/net/connman/iwd/0": {
            "net.connman.iwd.Device": {"Name": MockDBusValue("wlan0")}
        },
        "/net/connman/iwd/ignore_me": {
            "org.freedesktop.DBus.Introspectable": {}
        }
    }

    adapters = await client.get_adapters()
    assert len(adapters) == 1
    assert adapters[0]["path"] == "/net/connman/iwd/0"
    assert adapters[0]["name"] == "wlan0"


@pytest.mark.asyncio
async def test_set_powered_success(client, mock_bus):
    proxy_mock = MagicMock()
    device_interface_mock = AsyncMock()
    
    proxy_mock.get_interface.return_value = device_interface_mock
    mock_bus.get_proxy_object.return_value = proxy_mock

    await client.set_powered("/net/connman/iwd/0", True)

    mock_bus.introspect.assert_called_once_with(IWD_SERVICE, "/net/connman/iwd/0")
    device_interface_mock.set_powered.assert_called_once_with(True)


@pytest.mark.asyncio
async def test_set_powered_error(client, mock_bus):
    proxy_mock = MagicMock()
    device_interface_mock = AsyncMock()
    device_interface_mock.set_powered.side_effect = DBusError(
        "org.freedesktop.DBus.Error.Failed", "Operation failed"
    )
    
    proxy_mock.get_interface.return_value = device_interface_mock
    mock_bus.get_proxy_object.return_value = proxy_mock

    with pytest.raises(IwdError, match="Operation failed"):
        await client.set_powered("/net/connman/iwd/0", False)


@pytest.mark.asyncio
async def test_is_powered(client, mock_bus):
    proxy_mock = MagicMock()
    device_interface_mock = AsyncMock()
    device_interface_mock.get_powered.return_value = True
    
    proxy_mock.get_interface.return_value = device_interface_mock
    mock_bus.get_proxy_object.return_value = proxy_mock

    state = await client.is_powered("/net/connman/iwd/0")
    assert state is True


@pytest.mark.asyncio
async def test_scan_success(client, mock_bus):
    proxy_mock = MagicMock()
    station_interface_mock = AsyncMock()
    properties_interface_mock = MagicMock()
    
    proxy_mock.get_interface.side_effect = lambda iface: {
        "net.connman.iwd.Station": station_interface_mock,
        "org.freedesktop.DBus.Properties": properties_interface_mock
    }[iface]
    mock_bus.get_proxy_object.return_value = proxy_mock

    callback = None
    def capture_callback(cb):
        nonlocal callback
        callback = cb

    properties_interface_mock.on_properties_changed.side_effect = capture_callback

    async def simulate_scan_events():
        if callback:
            callback("net.connman.iwd.Station", {"Scanning": MockDBusValue(True)}, [])
            callback("net.connman.iwd.Station", {"Scanning": MockDBusValue(False)}, [])

    station_interface_mock.call_scan.side_effect = simulate_scan_events

    await client.scan("/net/connman/iwd/0")
    
    properties_interface_mock.on_properties_changed.assert_called_once()
    properties_interface_mock.off_properties_changed.assert_called_once_with(callback)


@pytest.mark.asyncio
async def test_get_networks(client, mock_manager):
    mock_manager.call_get_managed_objects.return_value = {
        "/net/connman/iwd/0/net1": {
            "net.connman.iwd.Network": {
                "Device": MockDBusValue("/net/connman/iwd/0"),
                "Name": MockDBusValue("Home_WiFi"),
                "Connected": MockDBusValue(False),
                "Type": MockDBusValue("psk")
            }
        },
        "/net/connman/iwd/0/net2": {
            "net.connman.iwd.Network": {
                "Device": MockDBusValue("/net/connman/iwd/different_adapter"),
                "Name": MockDBusValue("Office_WiFi"),
                "Connected": MockDBusValue(True),
                "Type": MockDBusValue("8021x")
            }
        }
    }

    networks = await client.get_networks("/net/connman/iwd/0")
    
    assert len(networks) == 1
    assert networks[0]["ssid"] == "Home_WiFi"
    assert networks[0]["path"] == "/net/connman/iwd/0/net1"
    assert networks[0]["security"] == "psk"


@pytest.mark.asyncio
async def test_disconnect_success(client, mock_bus):
    proxy_mock = MagicMock()
    station_interface_mock = AsyncMock()
    
    proxy_mock.get_interface.return_value = station_interface_mock
    mock_bus.get_proxy_object.return_value = proxy_mock

    await client.disconnect("/net/connman/iwd/0")
    station_interface_mock.call_disconnect.assert_called_once()


@pytest.mark.asyncio
async def test_connect_to_network_success(client, mock_bus):
    proxy_mock = MagicMock()
    network_interface_mock = AsyncMock()
    
    proxy_mock.get_interface.return_value = network_interface_mock
    mock_bus.get_proxy_object.return_value = proxy_mock

    network_payload = {"path": "/net/connman/iwd/0/net1", "ssid": "Home_WiFi"}
    result = await client.connect_to_network(network_payload)
    
    assert result == network_payload
    network_interface_mock.call_connect.assert_called_once()