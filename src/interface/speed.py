from typing import Any

import gi

from src.interface.gauge import Gauge
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib # type: ignore

class SpeedPage(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        self.set_margin_top(20)
        self.set_margin_bottom(20)
        self.set_margin_start(20)
        self.set_margin_end(20)
        
        self.start_callback: Any = None
        
        self.horizontal_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.horizontal_box.set_homogeneous(True)
        self.append(self.horizontal_box)
        
        self.gauges = {}
        
        self._create_gauge_column("ping", "ms", (1, 0.953, 0.557))
        self._create_gauge_column("download", "Mbps", (0.416, 1, 0.953))
        self._create_gauge_column("upload", "Mbps", (0.749, 0.443, 1))
        
        self.start_stack = Gtk.Stack()
        self.start_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)

        self.start_button = Gtk.Button(label="Test connection")
        self.start_button.set_halign(Gtk.Align.CENTER)
        self.start_button.add_css_class("suggested-action")
        self.start_button.add_css_class("pill")
        self.start_button.connect("clicked", self._on_start_clicked)
        self.start_stack.add_child(self.start_button)

        self.start_spinner = Adw.Spinner()
        self.start_spinner.set_margin_top(10)
        self.start_spinner.set_margin_bottom(10)
        self.start_stack.add_child(self.start_spinner)
        
        self.append(self.start_stack)
        
    def post_results(self, results: dict) -> None:
        self._update_gauge('ping', results['ping'], 400)

        download = results['download'] / 1000 / 1000
        upload = results['upload'] / 1000 / 1000
        
        # scale the gauges so that 100mb is halway through and 1000mb is max
        download_max = download * 0.8 + 200
        upload_max =  upload * 0.8 + 200
        
        self._update_gauge('download', download, download_max)
        self._update_gauge('upload', upload, upload_max)
        
    def reset_button(self) -> None:
        self.start_stack.set_visible_child(self.start_button)
        
    def _on_start_clicked(self, _) -> None:
        if self.start_callback:
            self.start_stack.set_visible_child(self.start_spinner)
            self.start_callback()

    def _create_gauge_column(self, title, unit, color) -> None:
        gauge_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        
        title_label = Gtk.Label()
        title_label.set_markup(f"<span weight='bold' size='10000' foreground='#888888'>{title.upper()}</span>")
        title_label.set_halign(Gtk.Align.CENTER)
        
        gauge = Gauge(color, unit)
        
        gauge_box.append(title_label)
        gauge_box.append(gauge)
        self.horizontal_box.append(gauge_box)
        
        self.gauges[title] = gauge

    def _update_gauge(self, name, value, max_value) -> None:
        self.gauges[name].set_value(value, max_value)