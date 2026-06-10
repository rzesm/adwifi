import asyncio
import gi

from src.interface.password_dialog import PasswordDialog
from src.interface.window import Window

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Adw, Gio, GLib # type: ignore


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