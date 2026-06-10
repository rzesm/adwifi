import dbus
import dbus.service

IWD_AGENT_INTERFACE = "net.connman.iwd.Agent"


class IwdAgent(dbus.service.Object):
    def __init__(self, bus, path, app):
        super().__init__(bus, path)
        self.app = app

    @dbus.service.method(IWD_AGENT_INTERFACE, in_signature="", out_signature="")
    def Release(self):
        self.app.current_request_path = None
        self.app.current_username = None

    @dbus.service.method(IWD_AGENT_INTERFACE, in_signature="o", out_signature="s")
    def RequestPassphrase(self, network):
        return self.app.consume_secret(str(network), kind="passphrase")

    @dbus.service.method(IWD_AGENT_INTERFACE, in_signature="o", out_signature="s")
    def RequestPrivateKeyPassphrase(self, network):
        return self.app.consume_secret(str(network), kind="private_key")

    @dbus.service.method(IWD_AGENT_INTERFACE, in_signature="os", out_signature="s")
    def RequestUserPassword(self, network, user):
        self.app.current_username = str(user) if user else None
        return self.app.consume_secret(str(network), kind="password")

    @dbus.service.method(IWD_AGENT_INTERFACE, in_signature="o", out_signature="ss")
    def RequestUserNameAndPassword(self, network):
        return self.app.consume_username_password(str(network))

    @dbus.service.method(IWD_AGENT_INTERFACE, in_signature="s", out_signature="")
    def Cancel(self, reason):
        self.app.current_request_path = None
        self.app.current_username = None