import threading
from time import sleep
from typing import Any

import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw # type: ignore


class NetworksPage(Adw.PreferencesPage):
    def __init__(self, refresher):
        super().__init__()
        self.networks_group = Adw.PreferencesGroup(title="Available networks")
        self.networks_group.set_header_suffix(refresher)
        self.rows = []
        
        self.connected_network_callback: Any = None
        self.disconnected_network_callback: Any = None
        
        self.add(self.networks_group)
        
    def on_network_clicked(
        self, row: Adw.ActionRow, status_stack: Gtk.Stack, network: dict
    ):
        if network['connected'] and self.connected_network_callback:
            self.connected_network_callback(network)
        elif self.disconnected_network_callback:
            # only add the spinner for connecting
            status_stack.set_visible_child_name("spinner")
            self.disconnected_network_callback(network)

    def update(self, networks: list):
        # remove existing rows
        for row in self.rows:
            self.networks_group.remove(row)
        self.rows.clear()
        
        # sort connected first
        networks = sorted(networks, key=lambda network: not network['connected'])
        
        # create new rows
        for network in networks:
            row = Adw.ActionRow()
            row.set_activatable(True)

            # checmark/spinner status
            status_stack = create_network_status_stack(network)
            row.add_prefix(status_stack)

            row.connect("activated", self.on_network_clicked, status_stack, network)
            
            # ssid (empty space for spacing)
            row.add_prefix(Gtk.Label(label=f"{network['ssid']} "))
            
            # security
            security_label = Gtk.Label(label=network['security'].upper())
            security_label.add_css_class("dim-label")
            row.add_suffix(security_label)

            self.networks_group.add(row)
            self.rows.append(row)
        
def create_network_status_stack(network: dict):
    status_stack = Gtk.Stack()
    status_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
    
    placeholder = Gtk.Box()
    status_stack.add_named(placeholder, "empty")
    
    checkmark = Gtk.Image.new_from_icon_name("object-select-symbolic")
    status_stack.add_named(checkmark, "checkmark")
    
    spinner = Adw.Spinner()
    status_stack.add_named(spinner, "spinner")
    
    if network['connected']:
        status_stack.set_visible_child_name("checkmark")
    else:
        status_stack.set_visible_child_name("empty")
        
    return status_stack


class NetworkRefresher(Gtk.Stack):
    def __init__(self):
        super().__init__()
        self.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        
        self.refresh_callback: Any = None 
        
        self.button = Gtk.Button(icon_name="view-refresh-symbolic")
        self.button.add_css_class("flat")
        self.button.connect("clicked", self.on_refresh_clicked)
        self.add_child(self.button)
        
        self.spinner = Adw.Spinner()
        self.spinner.set_margin_start(10)
        self.spinner.set_margin_end(10)
        self.add_child(self.spinner)
        
    def on_refresh_clicked(self, _):
        self.set_visible_child(self.spinner)
        if self.refresh_callback:
            self.refresh_callback()
            
    def reset(self):
        self.set_visible_child(self.button)