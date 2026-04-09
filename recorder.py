import time
import pyautogui
from pynput import mouse, keyboard

class Recorder:
    def __init__(self, add_action_callback, stop_callback):
        self.add_action_callback = add_action_callback
        self.stop_callback = stop_callback
        self.recording = False
        self.mouse_listener = None
        self.kb_listener = None
        self.last_time = 0

    def start(self):
        from models import ClickAction # Local import to avoid circular dependency
        self.recording = True
        self.last_time = time.time()
        self.mouse_listener = mouse.Listener(on_click=self.on_click)
        # We don't start the kb_listener here anymore, app.py will handle F10 toggle
        self.mouse_listener.start()

    def stop(self):
        self.recording = False
        if self.mouse_listener: self.mouse_listener.stop()
        self.stop_callback()

    def on_click(self, x, y, button, pressed):
        from models import ClickAction
        if pressed and self.recording:
            now = time.time()
            delay = round(now - self.last_time, 2)
            self.last_time = now
            action = ClickAction(int(x), int(y), button.name, "single", delay=delay)
            self.add_action_callback(action)
