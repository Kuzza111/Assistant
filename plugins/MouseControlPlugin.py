import pyautogui
import time
from core.plugin_base import PluginBase

class MouseControlPlugin(PluginBase):
    def init(self, core):
        self.core = core
        # Настройки безопасности pyautogui
        pyautogui.FAILSAFE = True  # Защита от случайного управления
        pyautogui.PAUSE = 0.1      # Пауза между действиями
        
        # Подписка на события управления мышью
        core.event_bus.subscribe('mouse_move', self.handle_mouse_move)
        core.event_bus.subscribe('mouse_click', self.handle_mouse_click)
        core.event_bus.subscribe('mouse_drag', self.handle_mouse_drag)
        core.event_bus.subscribe('mouse_scroll', self.handle_mouse_scroll)
        
        # Системные события
        core.event_bus.subscribe('system_shutdown', self.on_shutdown)
        
        self.core.event_bus.publish('output', "MouseControlPlugin initialized")

    def handle_mouse_move(self, data):
        """Перемещение мыши
        data: {'x': int, 'y': int, 'duration': float (optional)}
        """
        try:
            x = data.get('x')
            y = data.get('y')
            duration = data.get('duration', 0.2)
            
            if x is None or y is None:
                self.core.event_bus.publish('output', "Mouse move: missing coordinates")
                return
                
            pyautogui.moveTo(x, y, duration=duration)
            self.core.event_bus.publish('mouse_moved', {'x': x, 'y': y})
            
        except Exception as e:
            self.core.event_bus.publish('output', f"Mouse move error: {e}")

    def handle_mouse_click(self, data):
        """Клик мышью
        data: {
            'x': int (optional), 'y': int (optional), 
            'button': 'left'|'right'|'middle',
            'clicks': int, 'interval': float
        }
        """
        try:
            x = data.get('x')
            y = data.get('y')
            button = data.get('button', 'left')
            clicks = data.get('clicks', 1)
            interval = data.get('interval', 0.1)
            
            if x is not None and y is not None:
                pyautogui.click(x, y, clicks=clicks, interval=interval, button=button)
                self.core.event_bus.publish('mouse_clicked', {
                    'x': x, 'y': y, 'button': button, 'clicks': clicks
                })
            else:
                # Клик в текущей позиции
                pyautogui.click(clicks=clicks, interval=interval, button=button)
                current_pos = pyautogui.position()
                self.core.event_bus.publish('mouse_clicked', {
                    'x': current_pos.x, 'y': current_pos.y, 'button': button, 'clicks': clicks
                })
                
        except Exception as e:
            self.core.event_bus.publish('output', f"Mouse click error: {e}")

    def handle_mouse_drag(self, data):
        """Перетаскивание мышью
        data: {'to_x': int, 'to_y': int, 'from_x': int (optional), 'from_y': int (optional), 'duration': float}
        """
        try:
            to_x = data.get('to_x')
            to_y = data.get('to_y')
            duration = data.get('duration', 0.5)
            
            if to_x is None or to_y is None:
                self.core.event_bus.publish('output', "Mouse drag: missing destination coordinates")
                return
            
            # Используем текущую позицию, если не указана начальная
            from_x = data.get('from_x')
            from_y = data.get('from_y')
            
            if from_x is None or from_y is None:
                current_pos = self.get_mouse_position()
                from_x = from_x or current_pos['x']
                from_y = from_y or current_pos['y']
                
            pyautogui.drag(from_x, from_y, to_x - from_x, to_y - from_y, duration=duration)
            self.core.event_bus.publish('mouse_dragged', {
                'from': {'x': from_x, 'y': from_y},
                'to': {'x': to_x, 'y': to_y}
            })
            
        except Exception as e:
            self.core.event_bus.publish('output', f"Mouse drag error: {e}")

    def handle_mouse_scroll(self, data):
        """Прокрутка колесом мыши
        data: {'clicks': int (positive=up, negative=down), 'x': int (optional), 'y': int (optional)}
        """
        try:
            clicks = data.get('clicks', 1)
            x = data.get('x')
            y = data.get('y')
            
            if x is not None and y is not None:
                pyautogui.scroll(clicks, x=x, y=y)
            else:
                pyautogui.scroll(clicks)
                
            self.core.event_bus.publish('mouse_scrolled', {'clicks': clicks})
            
        except Exception as e:
            self.core.event_bus.publish('output', f"Mouse scroll error: {e}")

    def get_mouse_position(self):
        """Получение текущей позиции мыши"""
        pos = pyautogui.position()
        return {'x': pos.x, 'y': pos.y}

    def on_shutdown(self, event_data):
        self.shutdown()

    def shutdown(self):
        """Очистка ресурсов"""
        self.core.event_bus.publish('output', "MouseControlPlugin shutdown")

# Для совместимости с загрузчиком
Plugin = MouseControlPlugin