import asyncio

from dbus_next.errors import DBusError
from dbus_next.service import ServiceInterface, method

from adwifi.interface.application import Application


IWD_SERVICE = 'net.connman.iwd'
AGENT_MANAGER = "/net/connman/iwd"
AGENT_PATH = "/rzes/adwifi/agent"

class IwdAgent(ServiceInterface):
    @classmethod
    def connect_bus(cls, loop, bus):
        async def impl():
            agent = IwdAgent(bus, loop)

            # export the interface on the system bus
            bus.export(AGENT_PATH, agent)
            
            introspection = await bus.introspect(IWD_SERVICE, AGENT_MANAGER)
            manager_proxy = bus.get_proxy_object(IWD_SERVICE, AGENT_MANAGER, introspection)
            agent_manager = manager_proxy.get_interface("net.connman.iwd.AgentManager")
            
            # register the interface in iwd
            await agent_manager.call_register_agent(AGENT_PATH)
            
            return agent

        return asyncio.run_coroutine_threadsafe(impl(), loop).result()

    def __init__(self, bus, loop):
        super().__init__("net.connman.iwd.Agent")
        
        self._bus = bus
        self._loop = loop
        
    def connect_provider(self, provider: Application):
        self._provider = provider
        
    @method()
    async def RequestPassphrase(self, path: "o") -> "s": # type: ignore
        password = await self._provider.request_password(self._loop)
        if password: return password
        raise DBusError('net.connman.iwd.Error.Canceled', 'Passphrase request cancelled')

    @method()
    async def RequestUserNameAndPassword(self, network: "o") -> "(ss)": # type: ignore
        username, password = await self._provider.request_username_password(self._loop)
        if username and password: return username, password
        raise DBusError('net.connman.iwd.Error.Canceled', 'Passphrase request cancelled')

    @method()
    async def RequestUserPassword(self, network: "o", user: "s") -> "s": # type: ignore
        password = await self._provider.request_password(self._loop, user)
        if password: return password
        raise DBusError('net.connman.iwd.Error.Canceled', 'Passphrase request cancelled')

    @method()
    async def RequestPrivateKeyPassphrase(self, network: "o") -> "s": # type: ignore
        password = await self._provider.request_password(self._loop)
        if password: return password
        raise DBusError('net.connman.iwd.Error.Canceled', 'Passphrase request cancelled')

    @method()
    def Cancel(self, reason: "s"): # type: ignore
        pass

    @method()
    def Release(self):
        pass