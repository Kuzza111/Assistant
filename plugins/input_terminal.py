from core.plugin_base import PluginBase
import threading

class Plugin(PluginBase):
    def init(self, core):
        self.core = core
        core.event_bus.subscribe('user_input', self.on_startup)

    def on_startup(self, data):
        thread = threading.Thread(target=self.read_input)
        thread.start()

    def read_input(self):
        while True:
            user_input = input("> ")
            self.core.event_bus.publish('user_input', {'text': user_input})