import threading
from core.plugin_base import PluginBase

class ConsoleInputPlugin(PluginBase):
    def init(self, core):
        self.core = core
        threading.Thread(
            target=self.read_input,
            daemon=True
        ).start()

    def read_input(self):
        while self.core.running:
            try:
                user_input = input("> ").strip()
                self.core.event_bus.publish('user_input', user_input)
            except (EOFError, KeyboardInterrupt):
                self.core.event_bus.publish('output', "Input session closed")
                break
            except Exception as e:
                self.core.event_bus.publish('output', f"Input error: {e}")

Plugin = ConsoleInputPlugin