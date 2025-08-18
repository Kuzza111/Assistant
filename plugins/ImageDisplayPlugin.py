import cv2
import threading
import time
from core.plugin_base import PluginBase

class ImageDisplayPlugin(PluginBase):
    def init(self, core):
        self.core = core
        self.window_name = "AI Assistant Camera View"
        self.display_thread = None
        self.latest_frame = None
        self.display_active = False
        
        core.event_bus.subscribe('new_camera_frame', self.on_new_frame)
        core.event_bus.subscribe('system_shutdown', self.on_shutdown)
        
        self.start_display_thread() # starting display thread

    def on_new_frame(self, event_data):
        self.latest_frame = event_data['frame'] # just saving last frame

    def start_display_thread(self):
        if self.display_thread and self.display_thread.is_alive():
            return
            
        self.display_active = True
        self.display_thread = threading.Thread(target=self.display_loop)
        self.display_thread.daemon = True
        self.display_thread.start()
        self.core.event_bus.publish('output', "ImageDisplayPlugin: Started display thread")

    def display_loop(self): # main display loop
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.setWindowProperty(self.window_name, cv2.WND_PROP_TOPMOST, 1)  # Всегда поверх
        
        try:
            while self.display_active and self.core.running:
                if self.latest_frame is not None:
                    frame = self.latest_frame.copy()
                    
                    cv2.putText( # text instructions on screen
                        frame, 
                        "Press 'ESC' to close", 
                        (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 
                        0.7, 
                        (0, 255, 0), 
                        2
                    )
                    
                    cv2.imshow(self.window_name, frame)
                
                key = cv2.waitKey(25) & 0xFF
                if key == 27:  # ESC
                    self.display_active = False
                    break # надо бы заменить на вызов shutdown 
                
                time.sleep(0.01)
        finally:
            # always closing window on exit
            cv2.destroyWindow(self.window_name)

    def on_shutdown(self, event_data):
        self.shutdown()

    def shutdown(self):
        self.display_active = False
        if self.display_thread and self.display_thread != threading.current_thread():
            self.display_thread.join(timeout=1.0)
        
        # closing opencv window
        try:
            cv2.destroyWindow(self.window_name)
        except:
            pass
            
        self.core.event_bus.publish('output', "ImageDisplayPlugin shutdown")


Plugin = ImageDisplayPlugin # вроде работает и баз этого, но оставлю для совместимости с загрузчиком