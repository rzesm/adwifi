import asyncio
from concurrent.futures import Future
import gi

from adwifi.interface.username_password_dialog import UsernamePasswordDialog
from adwifi.interface.password_dialog import PasswordDialog
from adwifi.interface.window import Window

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Adw, Gio, GLib # type: ignore


class Application(Adw.Application):
    def __init__(self, future_backend: Future):
        super().__init__(
            application_id="rzes.adwifi", flags=Gio.ApplicationFlags.FLAGS_NONE
        )
        self._future_backend = future_backend

    def do_activate(self):
        self.window = Window(application=self)
        self.window.present()
        
        # link (and wait for) backend once the interface has initialised
        GLib.timeout_add(100, self.connect_backend)
        
    def connect_backend(self):
        iwd_agent, iwd_client, cache = self._future_backend.result()

        self.window.connect_cache(cache)
        self.window.connect_iwd_client(iwd_client)
        iwd_agent.connect_provider(self)
        
    def request_password(
        self, loop: asyncio.AbstractEventLoop, username: str | None = None
    ) -> asyncio.Future:
        future = loop.create_future()
        GLib.idle_add(self._prompt_password, future, loop, username)
        return future
    
    def request_username_password(
        self, loop: asyncio.AbstractEventLoop
    ) -> asyncio.Future:
        future = loop.create_future()
        GLib.idle_add(self._prompt_username_password, future, loop)
        return future
    
    def _prompt_password(
        self, future: asyncio.Future, loop: asyncio.AbstractEventLoop, 
        username: str | None
    ) -> None:
        dialog = PasswordDialog(username)

        def on_connect(button):
            password = dialog.get_password()
            loop.call_soon_threadsafe(future.set_result, password)
            dialog.close()

        def on_cancel(button):
            loop.call_soon_threadsafe(future.set_result, None)
            dialog.close()

        dialog.connect_connect_button(on_connect)
        dialog.connect_cancel_button(on_cancel)
        dialog.connect("closed", on_cancel)
        dialog.present(self.window)

    def _prompt_username_password(
        self, future: asyncio.Future, loop: asyncio.AbstractEventLoop
    ) -> None:
        dialog = UsernamePasswordDialog()

        def on_connect(button):
            username, password = dialog.get_username(), dialog.get_password()
            loop.call_soon_threadsafe(future.set_result, (username, password))
            dialog.close()

        def on_cancel(button):
            loop.call_soon_threadsafe(future.set_result, (None, None))
            dialog.close()

        dialog.connect_connect_button(on_connect)
        dialog.connect_cancel_button(on_cancel)
        dialog.connect("closed", on_cancel)
        dialog.present(self.window)