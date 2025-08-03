from core.plugin_base import PluginBase

class Plugin(PluginBase):
    def init(self, core):
        self.core = core
        # Подписка на события для вывода
        core.event_bus.subscribe('output_message', self.on_output_message)
        core.event_bus.subscribe('system_startup', self.on_startup)
        core.event_bus.subscribe('system_shutdown', self.on_shutdown)

    def shutdown(self):
        # Отписка от событий
        self.core.event_bus.unsubscribe('output_message', self.on_output_message)
        self.core.event_bus.unsubscribe('system_startup', self.on_startup)
        self.core.event_bus.unsubscribe('system_shutdown', self.on_shutdown)
        print("ConsoleOutputPlugin shutdown")  # Для отладки

    def on_startup(self, data):
        print("System started. Enter commands or input.")

    def on_shutdown(self, data):
        print("System shutting down.")

    def on_output_message(self, data):
        # Вывод сообщения (предполагаем, что data — dict с 'text')
        if 'text' in data:
            print(f"Output: {data['text']}")
        else:
            print("Output: [No text provided]")