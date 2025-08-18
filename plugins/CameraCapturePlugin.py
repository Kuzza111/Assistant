import cv2
import threading
import time
import numpy as np
from core.plugin_base import PluginBase

class CameraCapturePlugin(PluginBase):
    def init(self, core):
        self.core = core
        self.capture_thread = None
        self.running = False
        self.camera_index = 0  # Индекс камеры по умолчанию
        
        # Подписка на системные события
        core.event_bus.subscribe('system_shutdown', self.on_shutdown)
        
        # Запуск потока захвата
        self.start_capture()

    def start_capture(self):
        if self.capture_thread and self.capture_thread.is_alive():
            return
            
        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            self.core.event_bus.publish('output', f"CameraCapturePlugin: Cannot open camera {self.camera_index}")
            return
            
        self.running = True
        self.capture_thread = threading.Thread(target=self.capture_loop)
        self.capture_thread.daemon = True
        self.capture_thread.start()
        self.core.event_bus.publish('output', f"CameraCapturePlugin: Started capturing from camera {self.camera_index}")

    def capture_loop(self): # main loop
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                self.core.event_bus.publish('output', "CameraCapturePlugin: Failed to capture frame")
                time.sleep(1)
                continue
                
            # Публикация кадра на шину событий
            self.core.event_bus.publish(
                'new_camera_frame', 
                {
                    'frame': frame,
                    'timestamp': time.time(),
                    'source': f'camera_{self.camera_index}'
                }
            )
            
            time.sleep(0.033) # ~30 FPS

    def on_shutdown(self, event_data):
        """Обработчик завершения работы системы"""
        self.shutdown()

    def shutdown(self):
        """Остановка плагина и освобождение ресурсов"""
        self.running = False
        if self.capture_thread:
            self.capture_thread.join(timeout=1.0)
        if hasattr(self, 'cap'):
            self.cap.release()
        self.core.event_bus.publish('output', "CameraCapturePlugin shutdown")

Plugin = CameraCapturePlugin # не обязательно, но можно оставить для совместимости с загрузчиком