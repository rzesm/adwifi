import asyncio
from concurrent.futures import Future

from dbus_next.errors import DBusError

from typing import Any
from dbus_next.aio.message_bus import MessageBus


IWD_SERVICE = "net.connman.iwd"

class IwdError(RuntimeError):
    def __init__(self, message: str):
        super().__init__(message)

class IwdClient:
    _bus: MessageBus
    _manager: Any
    
    @classmethod
    def connect_bus(cls, loop, bus):
        async def impl():
            introspection = await bus.introspect(IWD_SERVICE, "/")
            proxy = bus.get_proxy_object(IWD_SERVICE, "/", introspection)
            manager: Any = proxy.get_interface("org.freedesktop.DBus.ObjectManager")
            
            return cls(bus, manager, loop)

        return asyncio.run_coroutine_threadsafe(impl(), loop).result()
        
    def __init__(self, bus, manager, loop):
        self._bus = bus
        self._manager = manager
        self._loop = loop

    def handle(self, request) -> Future:
        return asyncio.run_coroutine_threadsafe(request, self._loop)
        
    async def get_adapters(self) -> list[dict]:
        objects = (await self._manager.call_get_managed_objects()).items()
        return [
            {
                "path": path,
                "name": interfaces["net.connman.iwd.Device"]["Name"].value
            }
            for path, interfaces in objects
            if "net.connman.iwd.Device" in interfaces
        ]
        
    async def set_powered(self, adapter_path: str, state: bool) -> None:
        introspection = await self._bus.introspect(IWD_SERVICE, adapter_path)
        device_proxy = self._bus.get_proxy_object(IWD_SERVICE, adapter_path, introspection)
        device_interface: Any = device_proxy.get_interface("net.connman.iwd.Device")
        
        try:
            await device_interface.set_powered(state)
        except DBusError as e:
            raise IwdError(e.text)

    async def is_powered(self, device_path: str) -> bool:
        introspection = await self._bus.introspect(IWD_SERVICE, device_path)
        device_proxy = self._bus.get_proxy_object(IWD_SERVICE, device_path, introspection)
        device_interface: Any = device_proxy.get_interface("net.connman.iwd.Device")
        
        try:
            return await device_interface.get_powered()
        except DBusError as e:
            raise IwdError(e.text)
        
    async def scan(self, adapter_path: str) -> None:
        introspection = await self._bus.introspect(IWD_SERVICE, adapter_path)
        adapter_proxy = self._bus.get_proxy_object(IWD_SERVICE, adapter_path, introspection)
        station_interface: Any = adapter_proxy.get_interface("net.connman.iwd.Station")
        properties_interface: Any = adapter_proxy.get_interface("org.freedesktop.DBus.Properties")
        
        scan_started = False
        scan_finished = asyncio.Event()
        def check_for_scan_end(interface, changed_properties, invalidated_properties):
            nonlocal scan_started
            if "Scanning" in changed_properties:
                is_scanning = changed_properties["Scanning"].value
                
                if is_scanning:
                    scan_started = True
                elif scan_started and not is_scanning:
                    scan_finished.set()
        
        properties_interface.on_properties_changed(check_for_scan_end)
        
        try:
            await station_interface.call_scan()
            await asyncio.wait_for(scan_finished.wait(), timeout=10.0)
        finally:
            properties_interface.off_properties_changed(check_for_scan_end)

    async def get_networks(self, adapter_path: str) -> list[dict]:
        networks = []

        objects = (await self._manager.call_get_managed_objects()).items()
        for path, interfaces in objects:
            if "net.connman.iwd.Network" in interfaces:
                network_interface = interfaces["net.connman.iwd.Network"]
                
                device = network_interface.get("Device").value
                
                if device == adapter_path:
                    ssid = network_interface.get("Name").value
                    connected = network_interface.get("Connected").value
                    security = network_interface.get("Type").value
                    networks.append({
                        'path': path, 'ssid': ssid,
                        'connected': connected, 'security': security
                    })
                    
        return networks

    async def disconnect(self, adapter_path: str) -> None:
        introspection = await self._bus.introspect(IWD_SERVICE, adapter_path)
        adapter_proxy = self._bus.get_proxy_object(IWD_SERVICE, adapter_path, introspection)
        station_interface: Any = adapter_proxy.get_interface("net.connman.iwd.Station")
        
        try:
            await station_interface.call_disconnect()
        except DBusError as e:
            raise IwdError(e.text)

    async def connect_to_network(self, network: dict) -> dict | None:
        introspection = await self._bus.introspect(IWD_SERVICE, network['path'])
        network_proxy = self._bus.get_proxy_object(IWD_SERVICE, network['path'], introspection)
        network_interface: Any = network_proxy.get_interface("net.connman.iwd.Network")
        
        try:
            await network_interface.call_connect()
        except DBusError as e:
            raise IwdError(e.text)
            
        return network