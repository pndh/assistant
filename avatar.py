import gi
import numpy as np
import sounddevice as sd
import signal
import sys
import time

gi.require_version('Gtk', '3.0')
gi.require_version('GtkLayerShell', '0.1')
from gi.repository import Gtk, GtkLayerShell, GLib, Gdk

class NativeAvatar(Gtk.Window):
    def __init__(self):
        super().__init__()

        # 1. Native Wayland Transparency
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)
        self.set_app_paintable(True)

        # 2. Layer Shell Overlay
        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.BOTTOM, True)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.RIGHT, True)

        # Track margins for dragging
        self.margin_bottom = 20
        self.margin_right = 20
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.BOTTOM, self.margin_bottom)
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.RIGHT, self.margin_right)

        # 3. Avatar Images
        self.image = Gtk.Image()
        self.image.set_from_file("/home/pndhpndh/assistant/closed_kei.png")

        # 4. Drag & Drop EventBox (Wraps the image to catch mouse inputs)
        self.event_box = Gtk.EventBox()
        self.event_box.add(self.image)
        self.add(self.event_box)

        # Enable mouse tracking on the event box
        self.event_box.add_events(Gdk.EventMask.BUTTON_PRESS_MASK |
                                  Gdk.EventMask.BUTTON_RELEASE_MASK |
                                  Gdk.EventMask.POINTER_MOTION_MASK)

        self.event_box.connect("button-press-event", self.on_button_press)
        self.event_box.connect("button-release-event", self.on_button_release)
        self.event_box.connect("motion-notify-event", self.on_motion_notify)

        # Drag state variables
        self.dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0

        # 5. State Tracking
        self.is_talking = False
        self.last_sound_time = 0.0

        # We need to lock the sample rate to calculate frequencies accurately
        self.sample_rate = 16000

        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            blocksize=512,
            dtype='float32',
            callback=self.audio_callback
        )
        self.stream.start()

        GLib.timeout_add(100, self.update_ui)

    # --- Mouse Dragging Logic ---
    def on_button_press(self, widget, event):
        if event.button == 1:  # Left click
            self.dragging = True
            # Store where inside the window the user clicked
            self.drag_start_x = event.x
            self.drag_start_y = event.y
            return True
        return False

    def on_button_release(self, widget, event):
        if event.button == 1:
            self.dragging = False
            return True
        return False

    def on_motion_notify(self, widget, event):
        if self.dragging:
            # Calculate distance moved (surface-local coordinates)
            dx = event.x - self.drag_start_x
            dy = event.y - self.drag_start_y

            # Because we anchor to BOTTOM and RIGHT:
            # Moving right (positive dx) means we reduce the right margin
            # Moving down (positive dy) means we reduce the bottom margin
            self.margin_right -= dx
            self.margin_bottom -= dy

            # Apply the new margins to move the window
            GtkLayerShell.set_margin(self, GtkLayerShell.Edge.RIGHT, int(self.margin_right))
            GtkLayerShell.set_margin(self, GtkLayerShell.Edge.BOTTOM, int(self.margin_bottom))

            # Note: We do NOT update drag_start_x/y because moving the window
            # via margins under Wayland automatically resets the relative pointer coordinates.
            return True
        return False

    # --- Audio Logic ---
    def audio_callback(self, indata, frames, time_info, status):
        # 1. First, check the raw volume (Noise Gate)
        volume = np.linalg.norm(indata) * 10

        if volume > 2.0:
            # 2. If it's loud, check the PITCH (Frequency Gate)
            # Run the FFT to break the sound into frequencies
            fft_data = np.fft.rfft(indata[:, 0])
            frequencies = np.fft.rfftfreq(frames, 1.0 / self.sample_rate)

            # Find the loudest frequency in this chunk of audio
            peak_freq = frequencies[np.argmax(np.abs(fft_data))]

            # Human singing usually falls strictly between 80Hz (deep bass) and 1200Hz (soprano).
            # Keyboard clicks, clinking glass, and sirens are usually much higher.
            # Desk thuds are much lower.
            if 80 < peak_freq < 1200:
                self.last_sound_time = time.time()

        # 3. Smoothing Buffer (Keeps mouth open between lyrics)
        self.is_talking = (time.time() - self.last_sound_time) < 0.25

    def update_ui(self):
        if self.is_talking:
            self.image.set_from_file("/home/pndhpndh/assistant/open_kei.png")
        else:
            self.image.set_from_file("/home/pndhpndh/assistant/closed_kei.png")
        return True

    def cleanup(self):
        print("\nClosing audio stream safely...")
        self.stream.stop()
        self.stream.close()

def signal_handler(sig, frame):
    win.cleanup()
    Gtk.main_quit()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

win = NativeAvatar()
win.show_all()
Gtk.main()
