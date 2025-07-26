from core.plugin_base import PluginBase

class Plugin(PluginBase):
    def init(self, core):
        self.core = core
        core.event_bus.subscribe('user_input', self.on_action_execute)

    def on_action_execute(self, data):
        print(f"Output: {data['text']}")