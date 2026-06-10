import asyncio
from concurrent.futures import Future, ThreadPoolExecutor
import sys
from time import sleep
import gi

from src.interface.password_dialog import PasswordDialog
from src.speed_test_client import test_speed
from src.interface.speed import SpeedPage
from src.iwd_client import IwdClient
from src.interface.networks import NetworkRefresher, NetworksPage

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GLib # type: ignore


class Window(Adw.ApplicationWindow):
    def __init__(self, iwd_client: IwdClient, cache: dict, **kwargs):
        super().__init__(**kwargs)

        self.set_title("Wi-Fi Manager")
        
        self._iwd = iwd_client
        self._cache = cache
        
        self.network_refresher = NetworkRefresher()
        self.network_refresher.refresh_callback = lambda: self.request_update(
            self._iwd.handle(self._iwd.scan(self._cache['selected_adapter'])),
            self.on_scan_end
        )

        self.networks_page = NetworksPage(self.network_refresher)
        self.networks_page.connected_network_callback = \
            lambda _: self.request_update(
                self._iwd.handle(self._iwd.disconnect(self._cache['selected_adapter'])),
                self.on_disconnect
            )
        self.networks_page.disconnected_network_callback = \
            lambda network: self.request_update(
                self._iwd.handle(self._iwd.connect_to_network(network)),
                self.on_connect
            )

        self.speed_page = SpeedPage()
        self.speed_page.start_callback = \
            lambda: self.request_update(
                ThreadPoolExecutor().submit(asyncio.run, test_speed()),
                self.on_speed_test_end
            )
        
        self.toast_overlay = create_toast_overlay(
            create_view_stack(self.networks_page, self.speed_page)
        )
        self.set_content(self.toast_overlay)
        
        # begin with a network scan
        self.network_refresher.on_refresh_clicked(None)
        
    def on_scan_end(self, _):
        self.network_refresher.reset()
        self.update_networks()
        
    def on_disconnect(self, _):
        self.update_networks()

    def on_connect(self, _):
        self.update_networks()
        
    def on_speed_test_end(self, results):
        print(results)
        self.speed_page.post_results(results)
        self.speed_page.reset_button()

    def update_networks(self):
        #todo run this periodically
        self.request_update(
            self._iwd.handle(
                self._iwd.get_networks(self._cache['selected_adapter'])
            ),
            self.networks_page.update
        )
        
    def toast(self, message: str):
        toast = Adw.Toast(title=message)
        self.toast_overlay.add_toast(toast)
        
    # delegates update callbacks back to the main thread
    def request_update(self, request: Future, callback):
        assert callback != None

        def synchronize_callback(future: Future):
            # return 0 to run a one time task
            GLib.idle_add(lambda: (callback(future.result()), False)[1])

        request.add_done_callback(synchronize_callback)

def create_toast_overlay(view_stack):
    toast_overlay = Adw.ToastOverlay()
    
    toolbar_view = Adw.ToolbarView()

    header_bar = Adw.HeaderBar()

    menu_button = Gtk.Button(icon_name="open-menu-symbolic")
    header_bar.pack_start(menu_button)

    window_title = Adw.WindowTitle(title="Wi-Fi")
    header_bar.set_title_widget(window_title)

    wifi_switch = Gtk.Switch(active=True)
    wifi_switch.set_valign(Gtk.Align.CENTER)
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

    view_stack.add_titled(networks_page, "wifi_tab", " Networks")
    view_stack.add_titled(speed_page, "speed_tab", " Speed")
    
    return view_stack

class Application(Adw.Application):
    def __init__(self, iwd_client, cache):
        super().__init__(
            application_id="rzes.adwifi", flags=Gio.ApplicationFlags.FLAGS_NONE
        )
        self.iwd_client = iwd_client
        self.cache = cache

    def do_activate(self):
        self.window = Window(self.iwd_client, self.cache, application=self)
        self.window.present()
        
    def request_password(self, loop: asyncio.AbstractEventLoop) -> asyncio.Future:
        future = loop.create_future()
        GLib.idle_add(self._prompt_password, future, loop)
        return future
    
    def _prompt_password(self, future: asyncio.Future, loop: asyncio.AbstractEventLoop):
        dialog = PasswordDialog()

        def on_connect(button):
            password = dialog.get_password_text()
            loop.call_soon_threadsafe(future.set_result, password)
            dialog.close()

        def on_cancel(button):
            loop.call_soon_threadsafe(future.set_result, None)
            dialog.close()

        dialog.connect_connect_button(on_connect)
        dialog.connect_cancel_button(on_cancel)
        dialog.connect("closed", on_cancel)
        dialog.present(self.window)