import os
import importlib
import json
from .event_bus import EventBus
from .plugin_base import PluginBase

class Engine:
    def __init__(self, config_path='config.json'):
        self.event_bus = EventBus()
        self.plugins = {}
        self.config = self._load_config(config_path)
        self.running = False

    def _load_config(self, path):
        """Загрузка конфигурации из JSON"""
        if not os.path.exists(path):
            raise FileNotFoundError(f"Config file not found: {path}")
        try:
            with open(path, 'r') as f:
                return json.load(f) or {}
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in config: {e}")

    def register_plugin(self, name, plugin):
        """Регистрация плагина."""
        if not isinstance(plugin, PluginBase):
            raise ValueError("Plugin must inherit from PluginBase")
        if name in self.plugins:
            raise ValueError(f"Plugin '{name}' already registered")
        self.plugins[name] = plugin
        plugin.init(self)
        self.event_bus.publish('plugin_registered', {'name': name})

    def load_plugins(self, plugin_dir='plugins'):
        """Динамическая загрузка плагинов из конфига."""
        plugins_to_load = self.config.get('plugins', [])
        for plugin_name in plugins_to_load:
            self._load_single_plugin(plugin_name, plugin_dir)

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
            
            plugin_class = None
            for name, obj in vars(mod).items():
                if (isinstance(obj, type) and 
                    issubclass(obj, PluginBase) and 
                    obj is not PluginBase):
                    plugin_class = obj
                    break
            
            if not plugin_class:
                raise AttributeError(f"No PluginBase subclass found in {module_path}")
            
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
        self.running = False
        for name in list(self.plugins.keys()):
            self.remove_plugin(name)
        self.event_bus.publish('system_shutdown')

    def run(self):
        """Основной цикл приложения."""
        self.running = True
        self.event_bus.publish('system_startup')
        print("System started. Type 'exit' to shutdown")
        
        try:
            while self.running:
                try:
                    user_input = input("> ").strip()
                    self.event_bus.publish('user_input', user_input)
                except (EOFError, KeyboardInterrupt):
                    self.running = False
        finally:
            self.shutdown()
            print("Engine shutdown")