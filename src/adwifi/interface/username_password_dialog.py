import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw # type: ignore

class UsernamePasswordDialog(Adw.Dialog):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        main_box.set_margin_top(20)
        main_box.set_margin_bottom(20)
        main_box.set_margin_start(20)
        main_box.set_margin_end(20)
        
        title_label = Gtk.Label(label="Credentials required")
        title_label.add_css_class("title-2")
        title_label.set_halign(Gtk.Align.CENTER)
        main_box.append(title_label)
        
        list_box = Gtk.ListBox()
        list_box.add_css_class("boxed-list")
        
        self.username_row = Adw.EntryRow()
        self.username_row.set_title("Username")
        list_box.append(self.username_row)
        
        self.password_row = Adw.PasswordEntryRow()
        self.password_row.set_title("Password")
        self.password_row.set_activates_default(True) # connect with enter
        list_box.append(self.password_row)
        
        main_box.append(list_box)
        
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        
        self.cancel_button = Gtk.Button(label="Cancel")
        self.cancel_button.set_halign(Gtk.Align.START)
        
        self.connect_button = Gtk.Button(label="Connect")
        self.connect_button.add_css_class("suggested-action")
        self.connect_button.set_halign(Gtk.Align.END)
        
        button_box.append(self.cancel_button)
        button_box.append(Gtk.Box(hexpand=True)) # push the buttons to the corners
        button_box.append(self.connect_button)
        
        main_box.append(button_box)
        self.set_child(main_box)
        self.set_default_widget(self.connect_button)

    def get_username(self) -> str:
        return self.username_row.get_text()

    def get_password(self) -> str:
        return self.password_row.get_text()

    def connect_connect_button(self, callback):
        self.connect_button.connect("clicked", callback)

    def connect_cancel_button(self, callback):
        self.cancel_button.connect("clicked", callback)
