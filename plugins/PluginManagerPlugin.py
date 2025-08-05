from core.plugin_base import PluginBase

class PluginManagerPlugin(PluginBase):
    def init(self, core):
        self.core = core
        core.event_bus.subscribe('user_input', self.handle_input)
        core.event_bus.subscribe('system_startup', self.on_startup)

    def on_startup(self, event_data):
        self.core.event_bus.publish('output', "Plugin manager ready")

    def handle_input(self, user_input):
        if user_input.startswith('add '):
            self.handle_add(user_input[4:])
        elif user_input.startswith(('remove ', 'rm ')):
            plugin_name = user_input.split(maxsplit=1)[1]
            self.handle_remove(plugin_name)
    
    def handle_add(self, plugin_name):
        try:
            self.core.add_plugin(plugin_name)
            self.core.event_bus.publish('output', f"Added: {plugin_name}")
        except Exception as e:
            self.core.event_bus.publish('output', f"Add failed: {e}")

    def handle_remove(self, plugin_name):
        try:
            self.core.remove_plugin(plugin_name)
            self.core.event_bus.publish('output', f"Removed: {plugin_name}")
        except Exception as e:
            self.core.event_bus.publish('output', f"Remove failed: {e}")

Plugin = PluginManagerPlugin