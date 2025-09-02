import threading
import time
import tkinter as tk
from core.plugin_base import PluginBase

class StreamKeyboardControlPlugin(PluginBase):
    def init(self, core):
        self.core = core
        self.root = None
        self.thread = None
        self.running = False
        self.shutdown_requested = False
        self.key_states = {}  # Словарь состояний клавиш
        
        # Подписка на системные события
        core.event_bus.subscribe('system_shutdown', self.on_shutdown)
        
        # Запуск потока управления окном
        self.start_window_thread()

    def start_window_thread(self):
        """Запускает поток с GUI для управления клавиатурой"""
        if self.thread and self.thread.is_alive():
            return
            
        self.running = True
        self.thread = threading.Thread(target=self.create_window)
        self.thread.daemon = True
        self.thread.start()
        
        # Асинхронная публикация сообщения о запуске
        self.core.event_bus.publish(
            'output', 
            "KeyboardControlPlugin: Started keyboard control window",
            async_mode=True
        )

    def create_window(self):
        """Создает минимальное окно для захвата событий клавиатуры"""
        self.root = tk.Tk()
        self.root.title("Keyboard Control")
        self.root.geometry("100x100")  # Минимальный размер
        self.root.resizable(False, False)
        
        # Фокус на окно для захвата событий
        self.root.focus_set()
        
        # Привязка обработчиков клавиш
        self.root.bind('<KeyPress>', self.on_key_press)
        self.root.bind('<KeyRelease>', self.on_key_release)
        self.root.protocol("WM_DELETE_WINDOW", self.on_window_close)
        
        # Периодическая проверка флага завершения
        self.root.after(100, self.check_shutdown)
        
        self.root.mainloop()

    def check_shutdown(self):
        """Проверяет флаг завершения работы"""
        if self.shutdown_requested:
            self.root.destroy()
        else:
            self.root.after(100, self.check_shutdown)

    def on_key_press(self, event):
        """Обрабатывает нажатия клавиш"""
        key = event.keysym
        key_code = event.keycode
        
        # Определяем состояние (первое нажатие или автоповтор)
        state = "holded" if key in self.key_states else "pressed"
        self.key_states[key] = state
        
        # Отправка события на шину
        self.core.event_bus.publish(
            'keyboard_input',
            {
                'key': key,
                'code': key_code,
                'state': state,
                'timestamp': time.time()
            },
            async_mode=True
        )
            
    def on_key_release(self, event):
        """Обрабатывает отпускания клавиш"""
        key = event.keysym
        key_code = event.keycode
        
        # Обновляем состояние
        self.key_states[key] = "released"
        
        # Отправка события на шину
        self.core.event_bus.publish(
            'keyboard_input',
            {
                'key': key,
                'code': key_code,
                'state': "released",
                'timestamp': time.time()
            },
            async_mode=True
        )
            
        # Удаляем клавишу из состояния после отпускания
        self.root.after(100, lambda k=key: self.clear_key_state(k))

    def clear_key_state(self, key):
        """Удаляет клавишу из состояния"""
        if key in self.key_states and self.key_states[key] == "released":
            del self.key_states[key]

    def on_window_close(self):
        """Обрабатывает закрытие окна"""
        self.running = False
        self.root.destroy()
        self.core.event_bus.publish(
            'output', 
            "KeyboardControlPlugin: Window closed",
            async_mode=True
        )

    def on_shutdown(self, event_data):
        """Обработчик завершения работы системы"""
        self.shutdown()

    def shutdown(self):
        """Остановка плагина и освобождение ресурсов"""
        self.shutdown_requested = True
        self.running = False
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=0.5)
        
        self.core.event_bus.publish(
            'output', 
            "KeyboardControlPlugin shutdown"
        )

Plugin = StreamKeyboardControlPlugin