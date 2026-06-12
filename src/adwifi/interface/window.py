import asyncio
from concurrent.futures import Future, ThreadPoolExecutor
import gi

from adwifi.interface.menu import Menu
from adwifi.speed_test_client import run_speed_test
from adwifi.interface.speed_page import SpeedPage
from adwifi.iwd_client import IwdClient
from adwifi.interface.networks import NetworkRefresher, NetworksPage

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GLib # type: ignore


class Window(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.set_title("Wi-Fi Manager")
        
        self._wifi_switch = Gtk.Switch(active=True)
        self._wifi_switch.set_valign(Gtk.Align.CENTER)
        
        self._menu = Menu()
        self._network_refresher = NetworkRefresher()
        self._networks_page = NetworksPage(self._network_refresher)
        self._speed_page = SpeedPage()
        
        self._toast_overlay = create_toast_overlay(
            create_view_stack(self._networks_page, self._speed_page),
            self._menu, self._wifi_switch
        )
        self.set_content(self._toast_overlay)
        
    def connect_cache(self, cache: dict):
        self._cache = cache
        
    def connect_iwd_client(self, iwd_client: IwdClient):
        assert self._cache is not None

        self._iwd = iwd_client

        # menu actions
        about_action = Gio.SimpleAction.new("show_about")
        about_action.connect("activate", self._show_about)
        self.add_action(about_action)

        # adapter selection menu
        self._request_update(
            self._iwd.handle(self._iwd.get_adapters()),
            self._update_adapters
        )

        # callbacks
        self._wifi_switch.connect("notify::active", lambda switch, _: \
            self._request_update(
                self._iwd.handle(self._iwd.set_powered(
                    self._cache['selected_adapter'], switch.get_active()
                )),
                self._check_adapter_state
            )
        )
        self._networks_page.connected_network_callback = \
            lambda _: self._request_update(
                self._iwd.handle(self._iwd.disconnect(self._cache['selected_adapter'])),
                self._on_disconnect
            )
        self._networks_page.disconnected_network_callback = \
            lambda network: self._request_update(
                self._iwd.handle(self._iwd.connect_to_network(network)),
                self._on_connect
            )

        self._network_refresher.refresh_callback = lambda: self._request_update(
            self._iwd.handle(self._iwd.scan(self._cache['selected_adapter'])),
            self._on_scan_end
        )
        self._speed_page.start_callback = lambda: self._request_update(
            ThreadPoolExecutor().submit(asyncio.run, run_speed_test()),
            self._on_speed_test_end
        )

        self._update_networks()
        self._check_adapter_state(None)
        
    def toast(self, message: str):
        toast = Adw.Toast(title=message)
        self._toast_overlay.add_toast(toast)

    def _check_adapter_state(self, _):
        self._request_update(
            self._iwd.handle(self._iwd.is_powered(self._cache['selected_adapter'])),
            self._update_wifi_state
        )

    def _on_adapter_changed(self, action, parameter):
        adapter_path = parameter.get_string()
        self._cache['selected_adapter'] = adapter_path
        
    def _on_scan_end(self, _):
        self._network_refresher.reset()
        self._update_networks()
        
    def _on_disconnect(self, _):
        self._update_networks()

    def _on_connect(self, _):
        self._update_networks()
        
    def _on_speed_test_end(self, results):
        if results:
            self._speed_page.post_results(results)
        self._speed_page.reset_button()

    def _update_networks(self):
        self._request_update(
            self._iwd.handle(
                self._iwd.get_networks(self._cache['selected_adapter'])
            ),
            self._networks_page.update_networks
        )
        
    def _update_wifi_state(self, state: bool):
        self._wifi_switch.set_active(state)
        self._networks_page.set_wifi_state(state)
        if state: self._network_refresher.on_refresh_clicked(None)
        
    def _update_adapters(self, adapters: list[dict]) -> None:
        self._menu.update_adapters(adapters)

        # bind selection logic
        select_adapter_action = Gio.SimpleAction.new_stateful(
            "select_adapter",
            GLib.VariantType.new("s"), 
            GLib.Variant("s", self._cache['selected_adapter'])
        )
        select_adapter_action.connect("activate", self._on_adapter_changed)
        self.add_action(select_adapter_action)
        
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
        
    def _show_about(self, action, parameter):
        Adw.AboutDialog(
            application_name="Adwifi",
            version="0.1.0",
            developer_name="rzes",
            website="https://github.com/rzesm/adwifi",
            issue_url="https://github.com/rzesm/adwifi/issues",
            application_icon="network-wireless"
        ).present(self)

def create_toast_overlay(view_stack, menu, wifi_switch):
    toast_overlay = Adw.ToastOverlay()
    
    toolbar_view = Adw.ToolbarView()

    header_bar = Adw.HeaderBar()

    menu_button = Gtk.MenuButton(icon_name="open-menu-symbolic")
    menu_button.set_menu_model(menu)
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