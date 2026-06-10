import asyncio
import json
import sys
import threading

from dbus_next.constants import BusType

from src.interface.application import Application
from src.iwd_agent import IwdAgent
from src.iwd_client import IwdClient
from dbus_next.aio.message_bus import MessageBus

async def get_dbus():
    system_bus = MessageBus(bus_type=BusType.SYSTEM)
    await system_bus.connect()
    return system_bus

def main():
    # set up iwd interface daemon
    iwd_loop = asyncio.new_event_loop()

    def run_iwd_loop():
        asyncio.set_event_loop(iwd_loop)
        iwd_loop.run_forever()

    iwd_thread = threading.Thread(target=run_iwd_loop, daemon=True)
    iwd_thread.start()

    # load application cache
    with open("cache.json", 'r') as cache_file:
        #todo error handling
        cache: dict = json.load(cache_file)
    
    # launch iwd interfaces
    bus = asyncio.run_coroutine_threadsafe(get_dbus(), iwd_loop).result()
    iwd_client = IwdClient.connect_bus(iwd_loop, bus)
    iwd_agent = IwdAgent.connect_bus(iwd_loop, bus)
        
    # verify adapters
    adapters = iwd_client.handle(iwd_client.get_adapters()).result()
    if adapters:
        if cache['selected_adapter'] not in adapters:
            cache['selected_adapter'] = adapters[0]
    else:
        raise RuntimeError("main.py: no suitable wi-fi adapter was found") 
    
    # launch application
    application = Application(iwd_client, cache)
    iwd_agent.connect_provider(application)
    application.run(sys.argv)
    #todo prelaunch application for visually faster boot
    
if __name__ == "__main__":
    main()