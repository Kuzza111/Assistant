from core.plugin_base import PluginBase

class InputHandlerPlugin(PluginBase):
    def init(self, core):
        self.core = core
        core.event_bus.subscribe('user_input', self.handle_input)

    def handle_input(self, user_input):
        if not any([
            user_input.startswith('add '),
            user_input.startswith('rm '),
            user_input.startswith('remove '),
            user_input in ['exit', 'help', 'status']
        ]):
            self.core.event_bus.publish('user_message', {
                'text': user_input,
                'source': 'console'
            })

Plugin = InputHandlerPlugin