from collections import defaultdict
import threading

class EventBus:
    def __init__(self):
        self._subscribers = defaultdict(list)  # {event_type: [callbacks]}

    def subscribe(self, event_type, callback):
        """Подписаться на событие."""
        self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type, callback):
        """Отписаться от события."""
        if callback in self._subscribers[event_type]:
            self._subscribers[event_type].remove(callback)

    def publish(self, event_type, data=None, async_mode=False):
        """Опубликовать событие."""
        for callback in self._subscribers.get(event_type, []):
            if async_mode:
                threading.Thread(target=callback, args=(data,)).start()
            else:
                callback(data)