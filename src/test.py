import asyncio
from typing import Any
from dbus_next.aio.message_bus import MessageBus
from dbus_next.constants import BusType


async def list_networks():
    bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
    introspection = await bus.introspect("net.connman.iwd", "/")
    proxy = bus.get_proxy_object("net.connman.iwd", "/", introspection)
    manager: Any = proxy.get_interface("org.freedesktop.DBus.ObjectManager")
    objects = await manager.call_get_managed_objects()

    networks = []

    for path, interfaces in objects.items():
        if "net.connman.iwd.Network" in interfaces:
            network = interfaces["net.connman.iwd.Network"]

            name = network.get("Name")
            signal = network.get("SignalStrength")
            connected = network.get("Connected")

            networks.append({
                "path": path,
                "name": name.value if name else None,
                "signal": signal.value if signal else None,
                "connected": connected.value if connected else False
            })

    return networks

async def main():
    networks = await list_networks()

    for net in networks:
        print(f"{net['name']} | signal={net['signal']} | connected={net['connected']}")

asyncio.run(main())