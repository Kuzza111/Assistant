import pyautogui
import time
from core.plugin_base import PluginBase

class KeyboardControlPlugin(PluginBase):
    def init(self, core):
        self.core = core
        
        # Настройки безопасности
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.05  # Меньшая пауза для клавиатуры
        
        # Подписка на события клавиатуры
        core.event_bus.subscribe('keyboard_type', self.handle_type)
        core.event_bus.subscribe('keyboard_press', self.handle_press)
        core.event_bus.subscribe('keyboard_hotkey', self.handle_hotkey)
        core.event_bus.subscribe('keyboard_hold', self.handle_hold)
        
        # Системные события
        core.event_bus.subscribe('system_shutdown', self.on_shutdown)
        
        # Словарь алиасов клавиш (только там, где нужно преобразование)
        self.key_aliases = {
            'enter': 'enter',
            'return': 'enter', 
            'space': 'space',
            'spacebar': 'space',
            'escape': 'esc',
            'esc': 'esc',
            'backspace': 'backspace',
            'del': 'delete',
            'delete': 'delete',
            'pageup': 'pageup',
            'pagedown': 'pagedown',
            'pgup': 'pageup',
            'pgdn': 'pagedown',
            'ctrl': 'ctrl',
            'control': 'ctrl',
            'alt': 'alt',
            'shift': 'shift',
            'win': 'win',
            'windows': 'win',
            'cmd': 'cmd',
            'command': 'cmd'
        }
        
        self.core.event_bus.publish('output', "⌨KeyboardControlPlugin initialized")

    def handle_type(self, data):
        """Печать текста
        data: {'text': str, 'interval': float (optional)}
        """
        try:
            text = data.get('text', '')
            interval = data.get('interval', 0.05)
            
            if not text:
                self.core.event_bus.publish('output', "Keyboard type: no text provided")
                return
                
            pyautogui.write(text, interval=interval)
            self.core.event_bus.publish('keyboard_typed', {'text': text})
            
        except Exception as e:
            self.core.event_bus.publish('output', f"Keyboard type error: {e}")

    def handle_press(self, data):
        """Нажатие клавиши
        data: {'key': str, 'presses': int (optional)}
        """
        try:
            key = data.get('key', '')
            presses = data.get('presses', 1)
            
            if not key:
                self.core.event_bus.publish('output', "Keyboard press: no key provided")
                return
                
            # Проверяем алиасы клавиш
            if key.lower() in self.key_aliases:
                key = self.key_aliases[key.lower()]
                
            pyautogui.press(key, presses=presses)
            self.core.event_bus.publish('keyboard_pressed', {'key': key, 'presses': presses})
            
        except Exception as e:
            self.core.event_bus.publish('output', f"Keyboard press error: {e}")

    def handle_hotkey(self, data):
        """Горячие клавиши (комбинации)
        data: {'keys': [str] или str (через +)} - например ['ctrl', 'c'] или 'ctrl+c'
        """
        try:
            keys = data.get('keys', [])
            
            # Если передана строка, разбираем её
            if isinstance(keys, str):
                keys = [k.strip() for k in keys.split('+')]
            
            if not keys:
                self.core.event_bus.publish('output', "Keyboard hotkey: no keys provided")
                return
                
            # Преобразуем ключи через словарь алиасов
            processed_keys = []
            for key in keys:
                processed_key = self.key_aliases.get(key.lower(), key.lower())
                processed_keys.append(processed_key)
                
            pyautogui.hotkey(*processed_keys)
            self.core.event_bus.publish('keyboard_hotkey_pressed', {'keys': processed_keys})
            
        except Exception as e:
            self.core.event_bus.publish('output', f"Keyboard hotkey error: {e}")

    def handle_hold(self, data):
        """Удержание клавиши
        data: {'key': str, 'duration': float}
        """
        try:
            key = data.get('key', '')
            duration = data.get('duration', 1.0)
            
            if not key:
                self.core.event_bus.publish('output', "Keyboard hold: no key provided")
                return
                
            # Проверяем алиасы
            if key.lower() in self.key_aliases:
                key = self.key_aliases[key.lower()]
                
            pyautogui.keyDown(key)
            time.sleep(duration)
            pyautogui.keyUp(key)
            
            self.core.event_bus.publish('keyboard_held', {'key': key, 'duration': duration})
            
        except Exception as e:
            self.core.event_bus.publish('output', f"Keyboard hold error: {e}")

    def get_available_aliases(self):
        """Возвращает список доступных алиасов клавиш"""
        return list(self.key_aliases.keys())

    def on_shutdown(self, event_data):
        self.shutdown()

    def shutdown(self):
        """Очистка ресурсов"""
        self.core.event_bus.publish('output', "⌨KeyboardControlPlugin shutdown")

# Для совместимости с загрузчиком
Plugin = KeyboardControlPlugin