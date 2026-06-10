from __future__ import annotations

import sys
import traceback
from typing import Any, Dict, List, Optional, Tuple

import dbus
import dbus.mainloop.glib
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib, Gtk

from src.iwd_agent import IwdAgent
from interface.interface import WifiWindow
from network_item import NetworkItem


IWD_SERVICE = "net.connman.iwd"
IWD_ROOT = "/"
IWD_ADAPTER_INTERFACE = "net.connman.iwd.Adapter"
IWD_STATION_INTERFACE = "net.connman.iwd.Station"
IWD_NETWORK_INTERFACE = "net.connman.iwd.Network"
IWD_AGENT_MANAGER_INTERFACE = "net.connman.iwd.AgentManager"
DBUS_PROPERTIES_INTERFACE = "org.freedesktop.DBus.Properties"
DBUS_OBJECT_MANAGER_INTERFACE = "org.freedesktop.DBus.ObjectManager"


class WifiApp(Adw.Application):
    def __init__(self) -> None:
        super().__init__(
            application_id="com.example.WifiIwdFrontend",
            flags=Gio.ApplicationFlags.FLAGS_NONE,
        )
        self.window: Optional[WifiWindow] = None
        self.bus: Optional[dbus.SystemBus] = None
        self.agent: Optional[IwdAgent] = None
        self.agent_path = "/com/example/WifiIwdFrontend/Agent"
        self.current_request_path: Optional[str] = None
        self.current_username: Optional[str] = None
        self.pending_credentials: Dict[str, Dict[str, str]] = {}
        self.adapter_path: Optional[str] = None
        self.station_path: Optional[str] = None
        self.refresh_source_id: Optional[int] = None
        self.agent_registered = False

        self.connect("shutdown", self.on_shutdown)

    def _start_dbus(self) -> None:
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        self.bus = dbus.SystemBus()
        self.agent = IwdAgent(self.bus, self.agent_path, self)

        try:
            mgr = dbus.Interface(
                self.bus.get_object(IWD_SERVICE, IWD_ROOT),
                IWD_AGENT_MANAGER_INTERFACE,
            )
            mgr.RegisterAgent(dbus.ObjectPath(self.agent_path))
            self.agent_registered = True
        except dbus.DBusException:
            self.agent_registered = False

    def do_activate(self) -> None:
        if self.window is None:
            self.window = WifiWindow(self)
        self.window.present()
        self.refresh_adapter_state()
        self.schedule_refresh(0)
        self._start_dbus()

    def on_shutdown(self, *args) -> None:
        if self.refresh_source_id is not None:
            GLib.source_remove(self.refresh_source_id)
            self.refresh_source_id = None

        if self.agent_registered and self.bus is not None:
            try:
                mgr = dbus.Interface(
                    self.bus.get_object(IWD_SERVICE, IWD_ROOT),
                    IWD_AGENT_MANAGER_INTERFACE,
                )
                mgr.UnregisterAgent(dbus.ObjectPath(self.agent_path))
            except dbus.DBusException:
                pass

    def toast(self, message: str) -> None:
        if self.window is not None:
            self.window.toast_overlay.add_toast(Adw.Toast(title=message))

    def schedule_refresh(self, delay_seconds: int = 1) -> None:
        if self.refresh_source_id is not None:
            GLib.source_remove(self.refresh_source_id)
            self.refresh_source_id = None

        if delay_seconds <= 0:
            self.refresh_source_id = GLib.idle_add(self._refresh_timeout)
        else:
            self.refresh_source_id = GLib.timeout_add_seconds(
                delay_seconds, self._refresh_timeout
            )

    def _refresh_timeout(self) -> bool:
        self.refresh_source_id = None
        self.refresh_adapter_state()
        self.refresh_networks()
        return False

    def _managed_objects(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        def object_manager() -> Optional[dbus.Interface]:
            if self.bus is None:
                return None
            try:
                obj = self.bus.get_object(IWD_SERVICE, IWD_ROOT)
                return dbus.Interface(obj, DBUS_OBJECT_MANAGER_INTERFACE)
            except dbus.DBusException:
                return None

        mgr = object_manager()
        if mgr is None:
            return {}
        try:
            return mgr.GetManagedObjects()
        except dbus.DBusException:
            return {}

    def refresh_adapter_state(self) -> None:
        objects = self._managed_objects()

        adapter_path = None
        station_path = None

        for path, interfaces in objects.items():
            if IWD_ADAPTER_INTERFACE in interfaces and adapter_path is None:
                adapter_path = path

        if adapter_path is not None:
            for path, interfaces in objects.items():
                if IWD_STATION_INTERFACE in interfaces and path.startswith(adapter_path + "/"):
                    station_path = path
                    break

        self.adapter_path = adapter_path
        self.station_path = station_path

        if self.window is None:
            return

        if adapter_path is None:
            self.window.wifi_switch.set_sensitive(False)
            self.window.wifi_switch.set_active(False)
            self.window.status_label.set_text("iwd adapter not found")
            return

        self.window.wifi_switch.set_sensitive(True)
        powered = False#todo
        try:
            adapter_props = dbus.Interface(
                self.bus.get_object(IWD_SERVICE, adapter_path),
                DBUS_PROPERTIES_INTERFACE,
            )
            powered = bool(adapter_props.Get(IWD_ADAPTER_INTERFACE, "Powered"))
        except dbus.DBusException:
            powered = False

        self.window.wifi_switch.handler_block(self.window._wifi_switch_handler)
        self.window.wifi_switch.set_active(powered)
        self.window.wifi_switch.handler_unblock(self.window._wifi_switch_handler)

    def set_adapter_powered(self, powered: bool) -> None:
        if self.adapter_path is None or self.bus is None:
            self.toast("No Wi-Fi adapter found")
            return

        try:
            props = dbus.Interface(
                self.bus.get_object(IWD_SERVICE, self.adapter_path),
                DBUS_PROPERTIES_INTERFACE,
            )
            props.Set(IWD_ADAPTER_INTERFACE, "Powered", dbus.Boolean(powered))
            self.toast("Wi-Fi on" if powered else "Wi-Fi off")
            if powered:
                self.schedule_refresh(1)
            elif self.window is not None:
                self.window.set_networks([])
                self.window.stack.set_visible_child_name("empty")
        except dbus.DBusException as e:
            self.toast(f"Could not change power state: {self._dbus_error_text(e)}")

    def refresh_networks(self) -> None:
        if self.window is None:
            return

        self.window.set_loading(True)

        if self.adapter_path is None or self.station_path is None or self.bus is None:
            self.window.set_loading(False)
            self.window.set_networks([])
            self.toast("No station interface available yet")
            return

        try:
            adapter_powered = bool(
                dbus.Interface(
                    self.bus.get_object(IWD_SERVICE, self.adapter_path),
                    DBUS_PROPERTIES_INTERFACE,
                ).Get(IWD_ADAPTER_INTERFACE, "Powered")
            )
            if not adapter_powered:
                self.window.set_loading(False)
                self.window.set_networks([])
                return

            station = dbus.Interface(
                self.bus.get_object(IWD_SERVICE, self.station_path),
                IWD_STATION_INTERFACE,
            )

            try:
                station.Scan()
            except dbus.DBusException:
                pass

            objects = self._managed_objects()
            networks: List[NetworkItem] = []
            ordered_signal: Dict[str, int] = {}

            try:
                ordered = station.GetOrderedNetworks()
                for entry in ordered:
                    net_path = str(entry[0])
                    ordered_signal[net_path] = int(entry[1])
            except dbus.DBusException:
                ordered_signal = {}

            for path, interfaces in objects.items():
                if IWD_NETWORK_INTERFACE not in interfaces:
                    continue

                props = interfaces[IWD_NETWORK_INTERFACE]
                device = str(props.get("Device", ""))
                if device != self.station_path:
                    continue

                ssid = str(props.get("Name", "")) or "Hidden network"
                security = str(props.get("Type", ""))
                connected = bool(props.get("Connected", False))
                signal = int(ordered_signal.get(path, -10000))

                networks.append(
                    NetworkItem(
                        path=path,
                        ssid=ssid,
                        security=security,
                        signal=signal,
                        connected=connected,
                    )
                )

            networks.sort(
                key=lambda item: (not item.connected, -item.signal, item.ssid.lower())
            )
            self.window.set_loading(False)
            self.window.set_networks(networks)

        except dbus.DBusException as e:
            self.window.set_loading(False)
            self.window.set_networks([])
            self.toast(f"Refresh failed: {self._dbus_error_text(e)}")
        except Exception:
            self.window.set_loading(False)
            self.window.set_networks([])
            self.toast("Unexpected error while loading networks")
            traceback.print_exc()
            
    def interact_with_network(
        self, network_path: str, security: str, ssid: str, connected: bool
    ) -> None:
        if not connected:
            self._try_connect_network(network_path, security, ssid)
        else:
            self._disconnect()


    def _try_connect_network(self, network_path: str, security: str, ssid: str) -> None:
        if self.bus is None:
            return

        security = (security or "").lower()
        self.current_request_path = network_path
        self.current_username = None

        if security == "open":
            self._connect_network(network_path, ssid)
            return

        if security == "psk":
            self._prompt_password(network_path, ssid)
            return

        if security == "8021x":
            self._prompt_username_password(network_path, ssid)
            return

        self.toast(f"{ssid}: unsupported security type")

    def _prompt_password(self, network_path: str, ssid: str) -> None:
        if self.window is None:
            return

        dialog = Gtk.Dialog(
            transient_for=self.window,
            modal=True,
            title=f"Connect to {ssid}",
        )
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("Connect", Gtk.ResponseType.OK)
        dialog.set_default_response(Gtk.ResponseType.OK)

        area = dialog.get_content_area()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(16)
        box.set_margin_bottom(16)
        box.set_margin_start(16)
        box.set_margin_end(16)
        area.append(box)

        label = Gtk.Label(label="Password")
        label.set_xalign(0.0)
        box.append(label)

        entry = Gtk.PasswordEntry()
        entry.set_hexpand(True)
        box.append(entry)

        def on_response(dialog: Gtk.Dialog, response: Gtk.ResponseType) -> None:
            if response == Gtk.ResponseType.OK:
                self.pending_credentials[network_path] = {"passphrase": entry.get_text()}
                self._connect_network(network_path, ssid)
            dialog.destroy()

        dialog.connect("response", on_response)
        dialog.present()

    def _prompt_username_password(self, network_path: str, ssid: str) -> None:
        if self.window is None:
            return

        dialog = Gtk.Dialog(
            transient_for=self.window,
            modal=True,
            title=f"Connect to {ssid}",
        )
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("Connect", Gtk.ResponseType.OK)
        dialog.set_default_response(Gtk.ResponseType.OK)

        area = dialog.get_content_area()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(16)
        box.set_margin_bottom(16)
        box.set_margin_start(16)
        box.set_margin_end(16)
        area.append(box)

        user_label = Gtk.Label(label="Username")
        user_label.set_xalign(0.0)
        box.append(user_label)

        user_entry = Gtk.Entry()
        user_entry.set_hexpand(True)
        user_entry.set_activates_default(True)
        box.append(user_entry)

        pass_label = Gtk.Label(label="Password")
        pass_label.set_xalign(0.0)
        box.append(pass_label)

        pass_entry = Gtk.PasswordEntry()
        pass_entry.set_hexpand(True)
        pass_entry.set_activates_default(True)
        box.append(pass_entry)

        def on_response(dlg: Gtk.Dialog, response: Gtk.ResponseType) -> None:
            if response == Gtk.ResponseType.OK:
                self.pending_credentials[network_path] = {
                    "username": user_entry.get_text(),
                    "password": pass_entry.get_text(),
                }
                self._connect_network(network_path, ssid)
            dlg.destroy()

        dialog.connect("response", on_response)
        dialog.present()

    def _connect_network(self, network_path: str, ssid: str) -> None:
        if self.bus is None:
            return

        try:
            net = dbus.Interface(
                self.bus.get_object(IWD_SERVICE, network_path),
                IWD_NETWORK_INTERFACE,
            )
            net.Connect()
            self.toast(f"Connecting to {ssid}…")
            self.schedule_refresh(1)
        except dbus.DBusException as e:
            self.toast(f"Connection failed: {self._dbus_error_text(e)}")

    def _disconnect(self):
        if self.bus is None or self.station_path is None:
            return

        try:
            station = dbus.Interface(
                self.bus.get_object(IWD_SERVICE, self.station_path),
                IWD_STATION_INTERFACE,
            )
            station.Disconnect()
            self.toast("Disconnected")
            self.schedule_refresh(1)
        except dbus.DBusException as e:
            self.toast(f"Disconnection failed: {self._dbus_error_text(e)}")


    def consume_secret(self, network_path: str, kind: str = "passphrase") -> str:
        creds = self.pending_credentials.get(network_path, {})
        if kind == "private_key":
            value = creds.get("private_key_passphrase", "")
        elif kind == "password":
            value = creds.get("password", creds.get("passphrase", ""))
        else:
            value = creds.get("passphrase", creds.get("password", ""))

        if not value:
            raise dbus.DBusException(
                "Cancelled", name="net.connman.iwd.Agent.Error.Cancelled"
            )
        return value

    def consume_username_password(self, network_path: str) -> Tuple[str, str]:
        creds = self.pending_credentials.get(network_path, {})
        username = creds.get("username", self.current_username or "")
        password = creds.get("password", creds.get("passphrase", ""))
        if not username or not password:
            raise dbus.DBusException(
                "Cancelled", name="net.connman.iwd.Agent.Error.Cancelled"
            )
        return username, password

    def _dbus_error_text(self, error: Exception) -> str:
        if isinstance(error, dbus.DBusException):
            name = error.get_dbus_name() or ""
            msg = error.get_dbus_message() or ""
            if msg and name:
                return f"{name}: {msg}"
            return msg or name or str(error)
        return str(error)


def main() -> int:
    app = WifiApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())