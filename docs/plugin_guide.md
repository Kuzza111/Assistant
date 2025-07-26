# Руководство по написанию плагинов

Эта документация объясняет, как создавать и интегрировать плагины в систему. Плагины — это основной способ расширения функционала. Они позволяют добавлять новые возможности (например, обработку ввода, ИИ, действия) без изменения ядра (Engine).

## Почему плагины?
- **Модульность**: Каждый плагин независим и может быть добавлен/удален в runtime (hotswap).
- **Расширяемость**: Подписывайтесь на события через event bus и публикуйте свои.
- **Простота**: Наследуйте от `PluginBase` и реализуйте 2-3 метода.

## Шаги по созданию плагина
1. **Создайте файл в директории `/plugins/`**:
   - Имя файла: `<your_plugin_name>.py` (например, `my_input_plugin.py`).
   - Файл должен содержать класс `Plugin`, наследующий от `core.plugin_base.PluginBase`.

2. **Реализуйте базовый класс**:
   ```python
   from core.plugin_base import PluginBase

   class Plugin(PluginBase):
       def init(self, core):
           # Инициализация: подпишитесь на события
           core.event_bus.subscribe('user_input', self.my_handler)
           # Доступно: core.event_bus, core.config, core.plugins (для взаимодействия)

       def shutdown(self):
           # Очистка: закройте ресурсы, отпишитесь если нужно
           pass

       # Ваши обработчики событий
       def my_handler(self, data):
           print(f"Handled data: {data}")
           # Опубликуйте новое событие
           core.event_bus.publish('new_event', {'key': 'value'}, async_mode=True)