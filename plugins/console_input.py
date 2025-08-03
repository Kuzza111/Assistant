from core.plugin_base import PluginBase
import threading

class Plugin(PluginBase):
    def init(self, core):
        self.core = core
        self.input_thread = None  # Для отслеживания потока
        core.event_bus.subscribe('system_startup', self.on_startup)

    def shutdown(self):
        # Отписка от событий
        self.core.event_bus.unsubscribe('system_startup', self.on_startup)
        # Если поток существует, он завершится как daemon при shutdown системы
        self.input_thread = None
        print("ConsoleInputPlugin shutdown")  # Для отладки

    def on_startup(self, data):
        # Проверка: Запускаем thread только если он не существует или не активен
        if self.input_thread is None or not self.input_thread.is_alive():
            self.input_thread = threading.Thread(target=self.read_input)
            self.input_thread.daemon = True  # Завершится при shutdown
            self.input_thread.start()
        else:
            print("Input thread already running; skipping duplicate start.")  # Для отладки

    def read_input(self):
        while self.core.running:  # Синхронизируем с флагом Engine
            try:
                user_input = input("> ").strip()
                if user_input.startswith('add '):
                    plugin_name = user_input.split(' ', 1)[1]
                    try:
                        self.core.add_plugin(plugin_name)
                        print(f"Plugin '{plugin_name}' added.")  # Вывод в консоль (можно заменить на событие)
                    except ValueError as e:
                        print(f"Error adding plugin: {e}")
                elif user_input.startswith('remove '):
                    plugin_name = user_input.split(' ', 1)[1]
                    try:
                        self.core.remove_plugin(plugin_name)
                        print(f"Plugin '{plugin_name}' removed.")
                    except ValueError as e:
                        print(f"Error removing plugin: {e}")
                elif user_input == 'exit':
                    self.core.shutdown()
                    break
                else:
                    # Публикация события для другого ввода
                    self.core.event_bus.publish('user_input', {'text': user_input})
            except EOFError:  # Если input прерван (например, Ctrl+D)
                break
            except Exception as e:  # Общая обработка ошибок
                print(f"Input error: {e}")