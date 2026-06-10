import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw

class PasswordDialog(Adw.Dialog):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        main_box.set_margin_top(20)
        main_box.set_margin_bottom(20)
        main_box.set_margin_start(20)
        main_box.set_margin_end(20)
        
        title_label = Gtk.Label(label="Password Required")
        title_label.add_css_class("title-2")
        title_label.set_halign(Gtk.Align.CENTER)
        main_box.append(title_label)
        
        # 2. Password entry in the middle
        list_box = Gtk.ListBox()
        list_box.add_css_class("boxed-list")
        
        self.password_row = Adw.PasswordEntryRow()
        self.password_row.set_title("Password")
        self.password_row.set_activates_default(True)  # Permits 'Enter' key submission
        list_box.append(self.password_row)
        
        main_box.append(list_box)
        
        # 3. Buttons layout container for the bottom corners
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        
        # Bottom Left Button
        self.cancel_button = Gtk.Button(label="Cancel")
        self.cancel_button.set_halign(Gtk.Align.START)
        
        # Invisible expanding utility widget to push buttons to extreme corners
        spacer = Gtk.Box(hexpand=True)
        
        # Bottom Right Button
        self.connect_button = Gtk.Button(label="Connect")
        self.connect_button.add_css_class("suggested-action")
        self.connect_button.set_halign(Gtk.Align.END)
        
        # Order of assembly determines left-to-right alignment
        button_box.append(self.cancel_button)
        button_box.append(spacer)
        button_box.append(self.connect_button)
        
        main_box.append(button_box)
        
        # Set main box as the dialog root view child
        self.set_child(main_box)
        
        # Map the primary action hook to the connect button
        self.set_default_widget(self.connect_button)

    def get_password_text(self) -> str:
        """Returns the text currently entered into the password row."""
        return self.password_row.get_text()

    def connect_connect_button(self, callback):
        """Binds a click event handler to the Connect button."""
        self.connect_button.connect("clicked", callback)

    def connect_cancel_button(self, callback):
        """Binds a click event handler to the Cancel button."""
        self.cancel_button.connect("clicked", callback)