import sys
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, Gio # type: ignore


class Menu(Gio.Menu):
    def __init__(self):
        super().__init__()

        self.adapters_submenu = Gio.Menu()
        self.append_submenu("Adapters", self.adapters_submenu)

        self.append("About", "win.show_about")
        
    def update_adapters(self, adapters: list[dict]):
        self.adapters_submenu.remove_all()

        for adapter in adapters:
            self.adapters_submenu.append(
                adapter['name'], f"win.select_adapter('{adapter['path']}')"
            )