import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib # type: ignore
import math
import cairo

class Gauge(Gtk.Overlay):
    def __init__(self, color: tuple[float, float, float], unit: str):
        super().__init__()
        
        self.color = color
        self.unit = unit
        
        self.current_value = 0.0
        self.max_value = 100.0
        self.fraction = 0.0
        
        self.canvas = Gtk.DrawingArea()
        self.canvas.set_content_width(160)
        self.canvas.set_content_height(160)
        self.canvas.set_draw_func(self._draw_gauge)
        self.set_child(self.canvas)
        
        self.label = Gtk.Label()
        self.label.set_justify(Gtk.Justification.CENTER)
        self.label.set_halign(Gtk.Align.CENTER)
        self.label.set_valign(Gtk.Align.CENTER)
        self.add_overlay(self.label)
        
        # animation setup
        target = Adw.CallbackAnimationTarget.new(self._on_animation_tick)
        self.animation = Adw.TimedAnimation.new(self, 0.0, 0.0, 1000, target)
        self.animation.set_easing(Adw.Easing.EASE_OUT_CUBIC)
        
        self.set_value(0)

    def set_value(self, value, max_value=100.0):
        self.max_value = max_value
        
        # interrupt an ongoing animation
        if self.animation.get_state() == Adw.AnimationState.PLAYING:
            self.animation.pause()
            
        self.animation.set_value_from(self.current_value)
        self.animation.set_value_to(value)
        self.animation.play()

    # called every frame
    def _on_animation_tick(self, value):
        self.current_value = value
        self.fraction = min(1.0, max(0.0, self.current_value / self.max_value))
        
        self.label.set_markup(
            f"<span size='20000' weight='bold'>{self.current_value:.1f}</span>\n"
            f"<span size='8000' foreground='#888888'>{self.unit}</span>"
        )
        
        # redraw the progress stroke
        self.canvas.queue_draw()

    def _draw_gauge(self, area, context, width, height):
        center_x = width / 2
        center_y = height / 2
        radius = min(width, height) / 2 - 20

        start_angle = 0.75 * math.pi
        end_angle = 2.25 * math.pi
        total_angle = end_angle - start_angle

        # background stroke
        context.set_line_width(10)
        context.set_line_cap(cairo.LineCap.ROUND)
        context.set_source_rgba(0.5, 0.5, 0.5, 0.15)
        context.arc(center_x, center_y, radius, start_angle, end_angle)
        context.stroke()

        # progress stroke
        if self.fraction > 0:
            current_angle = start_angle + (total_angle * self.fraction)
            context.set_line_width(10)
            context.set_line_cap(cairo.LineCap.ROUND)
            context.set_source_rgba(self.color[0], self.color[1], self.color[2], 1.0)
            context.arc(center_x, center_y, radius, start_angle, current_angle)
            context.stroke()