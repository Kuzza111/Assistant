import json
import time
from core.plugin_base import PluginBase

class DebugEventPlugin(PluginBase):
    def init(self, core):
        self.core = core
        self.debug_mode = core.config.get('debug_mode', True)
        
        # Подписка на пользовательский ввод для debug команд
        core.event_bus.subscribe('user_input', self.handle_debug_commands)
        
        # Системные события
        core.event_bus.subscribe('system_startup', self.on_startup)
        core.event_bus.subscribe('system_shutdown', self.on_shutdown)
        
        self.core.event_bus.publish('output', "DebugEventPlugin initialized")

    def on_startup(self, event_data):
        if self.debug_mode:
            self.core.event_bus.publish('output', "Debug mode: ON")
            self.core.event_bus.publish('output', "Usage: debug <event_name> <json_data>")
            self.core.event_bus.publish('output', "       debug help - show help")

    def handle_debug_commands(self, user_input):
        """Обработка debug команд"""
        if not isinstance(user_input, str) or not user_input.startswith('debug '):
            return
            
        command_line = user_input[6:].strip()  # Убираем 'debug '
        
        if not command_line:
            self.show_help()
            return
            
        if command_line == 'help':
            self.show_help()
            return
            
        # Разделяем команду на event_name и данные
        parts = command_line.split(' ', 1)
        event_name = parts[0]
        
        if len(parts) == 1:
            # Только имя события - публикуем с пустыми данными
            self.publish_event(event_name, None)
        else:
            # Есть данные - пытаемся распарсить как JSON или отправляем как строку
            data_str = parts[1]
            self.publish_event(event_name, data_str)

    def publish_event(self, event_name, data_str):
        """Публикация события с данными"""
        try:
            # Определяем тип данных
            if data_str is None:
                event_data = {}
            elif data_str.strip().startswith(('{', '[')):
                # JSON данные
                event_data = json.loads(data_str)
            elif data_str.strip().lower() in ['true', 'false']:
                # Boolean
                event_data = data_str.strip().lower() == 'true'
            elif data_str.strip().isdigit():
                # Число
                event_data = int(data_str.strip())
            elif self._is_float(data_str.strip()):
                # Десятичное число
                event_data = float(data_str.strip())
            else:
                # Строка
                event_data = data_str.strip()
            
            # Публикуем событие
            self.core.event_bus.publish(event_name, event_data)
            
            # Подтверждение
            data_preview = str(event_data)[:100] + ('...' if len(str(event_data)) > 100 else '')
            self.core.event_bus.publish('output', f"Published '{event_name}': {data_preview}")
            
        except json.JSONDecodeError as e:
            self.core.event_bus.publish('output', f"Invalid JSON: {e}")
            self.core.event_bus.publish('output', f"Sending as string: '{data_str}'")
            # Отправляем как строку в случае ошибки JSON
            self.core.event_bus.publish(event_name, data_str)
        except Exception as e:
            self.core.event_bus.publish('output', f"Event publish error: {e}")

    def _is_float(self, value):
        """Проверка, является ли строка десятичным числом"""
        try:
            float(value)
            return '.' in value
        except ValueError:
            return False

    def show_help(self):
        """Показать справку по debug командам"""
        help_text = """
🔧 Debug Plugin Help:

Basic usage:
  debug <event_name> <data>    - Publish event with data
  debug <event_name>           - Publish event with empty data
  debug help                   - Show this help

Data formats:
  JSON object:   debug mouse_move {"x": 100, "y": 200}
  JSON array:    debug keyboard_hotkey ["ctrl", "c"]
  String:        debug keyboard_type Hello World
  Number:        debug mouse_scroll 3
  Boolean:       debug system_flag true

Common events to test:
  debug mouse_move {"x": 500, "y": 300}
  debug mouse_click {"button": "left"}
  debug keyboard_type {"text": "Hello World"}
  debug keyboard_press {"key": "enter"}
  debug keyboard_hotkey {"keys": ["ctrl", "c"]}
  debug screen_capture {}
  debug detect_objects_screen {}
  debug user_message {"text": "test message"}

Examples:
  debug output Testing debug plugin
  debug mouse_move {"x": 100, "y": 100, "duration": 0.5}
  debug keyboard_hotkey ["alt", "tab"]
        """
        self.core.event_bus.publish('output', help_text)

    def on_shutdown(self, event_data):
        self.shutdown()

    def shutdown(self):
        """Очистка ресурсов"""
        self.core.event_bus.publish('output', "DebugEventPlugin shutdown")

# Для совместимости с загрузчиком
Plugin = DebugEventPlugin