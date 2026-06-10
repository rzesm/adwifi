from typing import List

import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Adw, Gtk

from old.network_item import NetworkItem


def signal_icon(signal: int) -> str:
    # iwd reports signal as 100 * dBm, where 0 is strongest and -10000 is weakest.
    if signal >= -500:
        return "network-wireless-signal-excellent-symbolic"
    if signal >= -650:
        return "network-wireless-signal-good-symbolic"
    if signal >= -800:
        return "network-wireless-signal-ok-symbolic"
    if signal > -10000:
        return "network-wireless-signal-weak-symbolic"
    return "network-wireless-signal-none-symbolic"


def security_name(kind: str) -> str:
    kind = (kind or "").lower()
    if kind == "open":
        return "Open"
    if kind == "wep":
        return "WEP"
    if kind == "psk":
        return "PSK"
    if kind == "8021x":
        return "Enterprise"
    return kind.upper() if kind else "Unknown"


class WifiWindow(Adw.ApplicationWindow):
    def __init__(self, app) -> None:
        super().__init__(application=app)
        self.app = app
        self.set_title("Wi-Fi")
        self.set_default_size(420, 560)
        self.add_css_class("wifi-window")

        self.toast_overlay = Adw.ToastOverlay()
        self.set_content(self.toast_overlay)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.add_css_class("wifi-root")
        self.toast_overlay.set_child(root)

        header = Adw.HeaderBar()
        header.add_css_class("flat")
        root.append(header)

        title = Gtk.Label(label="Wi-Fi")
        title.add_css_class("title-1")
        title.set_valign(Gtk.Align.CENTER)
        header.set_title_widget(title)

        self.wifi_switch = Gtk.Switch()
        self.wifi_switch.set_valign(Gtk.Align.CENTER)
        self._wifi_switch_handler = self.wifi_switch.connect(
            "state-set", self.on_wifi_switch_state_set
        )
        header.pack_start(self.wifi_switch)

        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        body.set_margin_top(40)
        body.set_margin_bottom(40)
        body.set_margin_start(40)
        body.set_margin_end(40)
        root.append(body)

        self.status_label = Gtk.Label(label="")
        self.status_label.add_css_class("dim-label")
        self.status_label.set_wrap(True)
        self.status_label.set_xalign(0.0)
        body.append(self.status_label)

        self.stack = Gtk.Stack()
        self.stack.set_hexpand(True)
        self.stack.set_vexpand(True)
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        body.append(self.stack)

        self.list_box = Gtk.ListBox()
        self.list_box.add_css_class("boxed-list")
        self.list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.list_box.connect("row-activated", self.on_row_activated)
        self.list_box.set_vexpand(False)
        self.list_box.set_valign(Gtk.Align.START)
        self.list_box.set_margin_start(10)
        self.list_box.set_margin_end(10)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_child(self.list_box)
        self.stack.add_named(scrolled, "list")

        empty_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        empty_box.set_valign(Gtk.Align.CENTER)
        empty_box.set_halign(Gtk.Align.CENTER)
        empty_box.set_margin_top(48)
        empty_box.set_margin_bottom(48)
        empty_box.set_margin_start(24)
        empty_box.set_margin_end(24)

        empty_icon = Gtk.Image.new_from_icon_name("network-wireless-offline-symbolic")
        empty_icon.set_pixel_size(48)
        empty_box.append(empty_icon)

        empty_title = Gtk.Label(label="No networks found")
        empty_title.add_css_class("title-3")
        empty_box.append(empty_title)

        empty_subtitle = Gtk.Label(label="Turn Wi-Fi on, or try scanning again.")
        empty_subtitle.add_css_class("dim-label")
        empty_subtitle.set_wrap(True)
        empty_subtitle.set_justify(Gtk.Justification.CENTER)
        empty_box.append(empty_subtitle)

        self.stack.add_named(empty_box, "empty")

        self.spinner = Gtk.Spinner()
        self.spinner.set_halign(Gtk.Align.CENTER)
        self.spinner.set_valign(Gtk.Align.CENTER)
        spinner_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        spinner_box.append(self.spinner)
        self.stack.add_named(spinner_box, "loading")

        self.stack.set_visible_child_name("loading")
        self._apply_css()

    def _apply_css(self) -> None:
        css = b"""
        .boxed-list {
            border-radius: 18px;
        }

        .boxed-list row {
            padding: 10px;
        }

        .signal-pill {
            font-size: 0.9em;
            opacity: 0.85;
        }

        .network-row-title {
            font-weight: 600;
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_display(
            self.get_display(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def set_loading(self, loading: bool) -> None:
        if loading:
            self.spinner.start()
            self.stack.set_visible_child_name("loading")
        else:
            self.spinner.stop()

    def set_networks(self, items: List[NetworkItem]) -> None:
        while True:
            row = self.list_box.get_first_child()
            if row is None:
                break
            self.list_box.remove(row)

        if not items:
            self.stack.set_visible_child_name("empty")
            self.status_label.set_text("")
            return

        for item in items:
            row = Adw.ActionRow()
            row.path = item.path
            row.security = item.security
            row.ssid = item.ssid
            row.connected = item.connected
            
            row.set_activatable(True)

            row.set_title(item.ssid or "Hidden network")
            subtitle = security_name(item.security)
            if item.connected:
                subtitle = f"{subtitle} • Connected"
            row.set_subtitle(subtitle)

            signal = Gtk.Image.new_from_icon_name(signal_icon(item.signal))
            signal.add_css_class("signal-pill")
            signal.set_valign(Gtk.Align.CENTER)
            row.add_suffix(signal)

            if item.connected:
                check = Gtk.Image.new_from_icon_name("object-select-symbolic")
                check.set_valign(Gtk.Align.CENTER)
                row.add_suffix(check)

            self.list_box.append(row)

        self.stack.set_visible_child_name("list")
        self.status_label.set_text(
            f"{len(items)} network{'s' if len(items) != 1 else ''} available"
        )

    def on_wifi_switch_state_set(self, _switch: Gtk.Switch, state: bool) -> bool:
        self.app.set_adapter_powered(state)
        return False

    def on_row_activated(self, _listbox: Gtk.ListBox, row: Gtk.ListBoxRow) -> None:
        path = getattr(row, "path", None)
        security = getattr(row, "security", None)
        ssid = getattr(row, "ssid", None)
        connected = getattr(row, "connected", None)
        if not path:
            return
        self.app.interact_with_network(
            path,
            security or "",
            ssid or "",
            connected
        )