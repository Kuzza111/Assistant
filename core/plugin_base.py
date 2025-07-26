class PluginBase:
    def init(self, core):
        """Инициализация плагина. Доступ к core.event_bus, core.config и т.д."""
        pass

    def shutdown(self):
        """Очистка ресурсов перед удалением."""
        pass