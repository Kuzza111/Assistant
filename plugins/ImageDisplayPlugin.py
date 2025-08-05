import cv2
import threading
import time
from core.plugin_base import PluginBase

class ImageDisplayPlugin(PluginBase):
    def init(self, core):
        self.core = core  # Сохраняем ссылку на ядро
        self.window_name = "AI Assistant Camera View"
        self.display_thread = None
        self.latest_frame = None
        self.display_active = False
        
        # Подписка на события
        core.event_bus.subscribe('new_camera_frame', self.on_new_frame)
        core.event_bus.subscribe('system_shutdown', self.on_shutdown)
        
        # Запуск потока отображения
        self.start_display_thread()

    def on_new_frame(self, event_data):
        """Обработчик новых кадров с камеры"""
        # Просто сохраняем последний кадр
        self.latest_frame = event_data['frame']

    def start_display_thread(self):
        """Запускает поток отображения"""
        if self.display_thread and self.display_thread.is_alive():
            return
            
        self.display_active = True
        self.display_thread = threading.Thread(target=self.display_loop)
        self.display_thread.daemon = True
        self.display_thread.start()
        self.core.event_bus.publish('output', "✅ ImageDisplayPlugin: Started display thread")

    def display_loop(self):
        """Основной цикл отображения"""
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.setWindowProperty(self.window_name, cv2.WND_PROP_TOPMOST, 1)  # Всегда поверх
        
        try:
            while self.display_active and self.core.running:
                if self.latest_frame is not None:
                    frame = self.latest_frame.copy()
                    
                    # Добавляем текст с инструкцией
                    cv2.putText(
                        frame, 
                        "Press 'ESC' to close", 
                        (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 
                        0.7, 
                        (0, 255, 0), 
                        2
                    )
                    
                    cv2.imshow(self.window_name, frame)
                
                # Обработка клавиш (ESC для закрытия)
                key = cv2.waitKey(25) & 0xFF
                if key == 27:  # Код клавиши ESC
                    self.display_active = False
                    break
                
                time.sleep(0.01)
        finally:
            # Всегда закрываем окно при выходе
            cv2.destroyWindow(self.window_name)

    def on_shutdown(self, event_data):
        """Обработчик завершения работы системы"""
        self.shutdown()

    def shutdown(self):
        """Остановка плагина и освобождение ресурсов"""
        self.display_active = False
        if self.display_thread and self.display_thread != threading.current_thread():
            self.display_thread.join(timeout=1.0)
        
        # Закрываем окно OpenCV
        try:
            cv2.destroyWindow(self.window_name)
        except:
            pass
            
        self.core.event_bus.publish('output', "✅ ImageDisplayPlugin shutdown")

# Для совместимости с загрузчиком
Plugin = ImageDisplayPlugin