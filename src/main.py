import asyncio
from concurrent.futures import ThreadPoolExecutor
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

async def set_up_backend(cache: dict) -> tuple:
    # set up iwd interface daemon
    iwd_loop = asyncio.new_event_loop()

    def run_iwd_loop():
        asyncio.set_event_loop(iwd_loop)
        iwd_loop.run_forever()

    iwd_thread = threading.Thread(target=run_iwd_loop, daemon=True)
    iwd_thread.start()
    
    # launch iwd interfaces
    bus = asyncio.run_coroutine_threadsafe(get_dbus(), iwd_loop).result()
    iwd_client = IwdClient.connect_bus(iwd_loop, bus)
    iwd_agent = IwdAgent.connect_bus(iwd_loop, bus)
        
    # verify adapters
    adapters = iwd_client.handle(iwd_client.get_adapters()).result()
    if adapters:
        adapter_paths = [adapter['path'] for adapter in adapters]
        
        if cache['selected_adapter'] not in adapter_paths:
            cache['selected_adapter'] = adapters[0]['path']
    else:
        raise RuntimeError("No suitable Wi-Fi adapter was found")
    
    return iwd_agent, iwd_client, cache

def load_cache() -> dict:
    default_cache = {
        'selected_adapter': ''
    }

    try:
        with open("cache.json", 'r') as cache_file:
            cache: dict = json.load(cache_file)
            if not isinstance(cache, dict): raise TypeError()
            
            # verify presence of keys
            cache['selected_adapter']
            
            return cache
    except Exception:
        return default_cache

def save_cache(cache: dict):
    try:
        with open("cache.json", 'w') as cache_file:
            json.dump(cache, cache_file)
    except Exception:
        pass

def main():
    # load cache
    cache = load_cache()

    # set up backend on another thread
    future_backend = ThreadPoolExecutor().submit(asyncio.run, set_up_backend(cache))
    
    # launch application
    application = Application(future_backend)
    application.run(sys.argv)

    save_cache(cache)
    
if __name__ == "__main__":
    main()