import asyncio
from concurrent.futures import Future, ThreadPoolExecutor
import gi

from src.speed_test_client import test_speed
from src.interface.speed_page import SpeedPage
from src.iwd_client import IwdClient
from src.interface.networks import NetworkRefresher, NetworksPage

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GLib # type: ignore


class Window(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.set_title("Wi-Fi Manager")
        
        self.wifi_switch = Gtk.Switch(active=True)
        self.wifi_switch.set_valign(Gtk.Align.CENTER)
        
        self.network_refresher = NetworkRefresher()
        self.networks_page = NetworksPage(self.network_refresher)
        self.speed_page = SpeedPage()
        
        self.toast_overlay = create_toast_overlay(
            create_view_stack(self.networks_page, self.speed_page),
            self.wifi_switch
        )
        self.set_content(self.toast_overlay)
        
    def connect_cache(self, cache: dict):
        self._cache = cache
        
    def connect_iwd_client(self, iwd_client: IwdClient):
        assert self._cache is not None

        self._iwd = iwd_client

        self.wifi_switch.connect("notify::active", lambda switch, _: \
            self._request_update(
                self._iwd.handle(self._iwd.set_powered(
                    self._cache['selected_adapter'], switch.get_active()
                )),
                self._check_adapter_state
            )
        )
        self.networks_page.connected_network_callback = \
            lambda _: self._request_update(
                self._iwd.handle(self._iwd.disconnect(self._cache['selected_adapter'])),
                self._on_disconnect
            )
        self.networks_page.disconnected_network_callback = \
            lambda network: self._request_update(
                self._iwd.handle(self._iwd.connect_to_network(network)),
                self._on_connect
            )

        self.network_refresher.refresh_callback = lambda: self._request_update(
            self._iwd.handle(self._iwd.scan(self._cache['selected_adapter'])),
            self._on_scan_end
        )
        self.speed_page.start_callback = lambda: self._request_update(
            ThreadPoolExecutor().submit(asyncio.run, test_speed()),
            self._on_speed_test_end
        )

        self._update_networks()
        self._check_adapter_state(None)
        
    def toast(self, message: str):
        toast = Adw.Toast(title=message)
        self.toast_overlay.add_toast(toast)

    def _check_adapter_state(self, _):
        self._request_update(
            self._iwd.handle(self._iwd.is_powered(self._cache['selected_adapter'])),
            self._update_wifi_state
        )
        
    def _on_scan_end(self, _):
        self.network_refresher.reset()
        self._update_networks()
        
    def _on_disconnect(self, _):
        self._update_networks()

    def _on_connect(self, _):
        self._update_networks()
        
    def _on_speed_test_end(self, results):
        if results:
            self.speed_page.post_results(results)
        self.speed_page.reset_button()

    def _update_networks(self):
        self._request_update(
            self._iwd.handle(
                self._iwd.get_networks(self._cache['selected_adapter'])
            ),
            self.networks_page.update_networks
        )
        
    def _update_wifi_state(self, state: bool):
        self.wifi_switch.set_active(state)
        self.networks_page.set_wifi_state(state)
        if state: self.network_refresher.on_refresh_clicked(None)
        
    # delegates interface update callbacks back to the main thread
    def _request_update(self, request: Future, callback, toast_errors = True):
        assert callback != None

        def update(future: Future):
            try:
                callback(future.result())
            except Exception as e:
                string = str(e)
                # capitalize first letter
                message = string[0].upper() + string[1:]
                if toast_errors: self.toast(message)
                # call the callback without the result anyway
                callback(None)

        def synchronize_callback(future: Future):
            # return 0 to run a one time task
            GLib.idle_add(update, future)

        request.add_done_callback(synchronize_callback)

def create_toast_overlay(view_stack, wifi_switch):
    toast_overlay = Adw.ToastOverlay()
    
    toolbar_view = Adw.ToolbarView()

    header_bar = Adw.HeaderBar()

    menu_button = Gtk.Button(icon_name="open-menu-symbolic")
    header_bar.pack_start(menu_button)

    window_title = Adw.WindowTitle(title="Wi-Fi")
    header_bar.set_title_widget(window_title)

    header_bar.pack_end(wifi_switch)

    toolbar_view.add_top_bar(header_bar)

    action_bar = Gtk.ActionBar()

    stack_switcher = Gtk.StackSwitcher()
    stack_switcher.set_stack(view_stack)
    action_bar.set_center_widget(stack_switcher)

    toolbar_view.add_bottom_bar(action_bar)

    toolbar_view.set_content(view_stack)

    toast_overlay.set_child(toolbar_view)
    
    return toast_overlay
        
def create_view_stack(networks_page, speed_page):
    view_stack = Gtk.Stack()
    view_stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
    view_stack.set_transition_duration(300)

    view_stack.add_titled(networks_page, "networks_page", " Networks")
    view_stack.add_titled(speed_page, "speed_page", " Speed")
    
    return view_stack