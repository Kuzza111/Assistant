from core.plugin_base import PluginBase

class SystemCommandsPlugin(PluginBase):
    def init(self, core):
        self.core = core
        core.event_bus.subscribe('user_input', self.handle_input)
        core.event_bus.subscribe('system_startup', self.on_startup)

    def on_startup(self, event_data):
        self.core.event_bus.publish('output', "System commands ready")

    def handle_input(self, user_input):
        commands = {
            'exit': self.handle_exit,
            'help': self.handle_help,
            'status': self.handle_status
        }
        if user_input in commands:
            commands[user_input]()

    def handle_exit(self):
        self.core.event_bus.publish('output', "Shutting down...")
        self.core.running = False

    def handle_help(self):
        help_text = "\n".join([
            "Available commands:",
            "  exit    - Shutdown system",
            "  status  - Show system info",
            "  add X   - Load plugin X",
            "  rm X    - Unload plugin X"
        ])
        self.core.event_bus.publish('output', help_text)

    def handle_status(self):
        status = {
            "running": self.core.running,
            "plugins": list(self.core.plugins.keys())
        }
        self.core.event_bus.publish('output', status)

# Для совместимости с загрузчиком
Plugin = SystemCommandsPlugin