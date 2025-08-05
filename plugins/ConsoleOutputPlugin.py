from core.plugin_base import PluginBase

class ConsoleOutputPlugin(PluginBase):
    def init(self, core):
        self.core = core
        core.event_bus.subscribe('output', self.handle_output)
        core.event_bus.subscribe('system_startup', self.handle_system_event)
        core.event_bus.subscribe('system_shutdown', self.handle_system_event)

    def handle_output(self, data):
        if isinstance(data, str):
            print(data)
        elif isinstance(data, dict):
            print(f"[{data.get('type', 'INFO')}] {data.get('text', '')}")
        else:
            print(f"Output: {str(data)}")

    def handle_system_event(self, event_type):
        messages = {
            'system_startup': "🚀 System started",
            'system_shutdown': "🛑 System shutting down"
        }
        print(messages.get(event_type, f"System event: {event_type}"))

Plugin = ConsoleOutputPlugin