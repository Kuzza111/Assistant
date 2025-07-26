import os
import importlib
import yaml  # Для чтения config.yaml
from .event_bus import EventBus
from .plugin_base import PluginBase

class Engine:
    def __init__(self, config_path='config.yaml'):
        self.event_bus = EventBus()
        self.plugins = {}  # {name: plugin_instance}
        self.config = self._load_config(config_path)

    def _load_config(self, path):
        """Загрузка конфигурации из YAML."""
        if not os.path.exists(path):
            raise FileNotFoundError(f"Config file not found: {path}")
        with open(path, 'r') as f:
            return yaml.safe_load(f) or {}

    def register_plugin(self, name, plugin):
        """Регистрация плагина."""
        if not isinstance(plugin, PluginBase):
            raise ValueError("Plugin must inherit from PluginBase")
        if name in self.plugins:
            raise ValueError(f"Plugin '{name}' already registered")
        self.plugins[name] = plugin
        plugin.init(self)  # Инициализация
        self.event_bus.publish('plugin_registered', {'name': name})

    def load_plugins(self, plugin_dir='plugins'):
        """Динамическая загрузка плагинов из конфига."""
        plugins_to_load = self.config.get('plugins', [])
        for plugin_name in plugins_to_load:
            self._load_single_plugin(plugin_name, plugin_dir)

        # Проверка required_plugins
        required = set(self.config.get('required_plugins', []))
        loaded = set(self.plugins.keys())
        missing = required - loaded
        if missing:
            raise ValueError(f"Missing required plugins: {missing}")

    def _load_single_plugin(self, plugin_name, plugin_dir):
        """Вспомогательный метод для загрузки одного плагина."""
        try:
            module_path = f'{plugin_dir}.{plugin_name}'
            mod = importlib.import_module(module_path)
            plugin_class = getattr(mod, 'Plugin', None)
            if not plugin_class:
                raise AttributeError(f"No 'Plugin' class in {module_path}")
            plugin = plugin_class()
            self.register_plugin(plugin_name, plugin)
        except (ImportError, AttributeError) as e:
            raise ValueError(f"Failed to load plugin '{plugin_name}': {e}")

    def add_plugin(self, name, plugin_dir='plugins'):
        """Hotswap: Добавить плагин в runtime."""
        self._load_single_plugin(name, plugin_dir)

    def remove_plugin(self, name):
        """Hotswap: Удалить плагин в runtime."""
        if name not in self.plugins:
            raise ValueError(f"Plugin '{name}' not found")
        plugin = self.plugins.pop(name)
        plugin.shutdown()
        self.event_bus.publish('plugin_removed', {'name': name})

    def shutdown(self):
        """Завершение работы: shutdown всех плагинов."""
        for name in list(self.plugins.keys()):
            self.remove_plugin(name)  # Используем remove для hotswap-логики
        self.event_bus.publish('system_shutdown')

    def run(self):
        """Основной цикл приложения. Для примера: симуляция ввода через консоль."""
        self.event_bus.publish('system_startup')
        print("Engine running. Type commands (e.g., 'input: hello') or 'add <plugin>' or 'remove <plugin>' or 'exit'.")
        while True:
            user_input = input("> ").strip()
            if user_input == 'exit':
                break
            elif user_input.startswith('add '):
                plugin_name = user_input.split(' ', 1)[1]
                try:
                    self.add_plugin(plugin_name)
                    print(f"Plugin '{plugin_name}' added.")
                except ValueError as e:
                    print(e)
            elif user_input.startswith('remove '):
                plugin_name = user_input.split(' ', 1)[1]
                try:
                    self.remove_plugin(plugin_name)
                    print(f"Plugin '{plugin_name}' removed.")
                except ValueError as e:
                    print(e)
            elif user_input.startswith('input: '):
                data = user_input.split(':', 1)[1].strip()
                self.event_bus.publish('user_input', {'text': data})
            else:
                print("Unknown command.")

        self.shutdown()
        print("Engine shutdown.")