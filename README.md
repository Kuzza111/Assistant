Modular assistanr for your PC and more!
# AI Assistant project

The AI Assistant is designed to help users with everyday and technical tasks by controlling a PC or other headless devices (e.g., robots, embedded systems, or servers).

## Architecture

The architecture is based on an **event-driven** approach using a plugin system, where the core (Engine) orchestrates interactions between components via an Event Bus. This ensures decoupling (separation of dependencies), making it easier to add new features without modifying the core code.

### Overall Project Structure

```
project/
├── core/                  # System core (minimal, without business logic)
│   ├── __init__.py        # To designate as a package
│   ├── engine.py          # Central orchestrator
│   ├── event_bus.py       # Event bus
│   └── plugin_base.py     # Base class for plugins
├── plugins/               # Directory for all plugins (built-in and user-defined)
│   └── example_plugin.py  # Example plugin
├── config.json            # Configuration file (list of plugins and settings)
├── main.py                # Entry point for launching
└── README.md              # This file
```

- **Core**: Minimal core responsible for loading, management, and coordination.
- **Plugins**: All functionality is implemented as plugins (no separate directory for "modules" — everything is unified for maximum flexibility).
- **Config**: JSON file for configuration (e.g., which plugins to load).

### How the System Works Overall

1. **Launch**: `main.py` creates the Engine, loads plugins, and starts `run()`.
2. **Event Processing**:
    - User inputs a command → Publication of `user_input`.
    - A plugin (e.g., AI) processes it and publishes `action_execute`.
    - An action plugin executes (e.g., mouse click).
3. **Hotswap Example**: In runtime: `engine.add_plugin('new_ai_plugin')` — the plugin is loaded, initialized, and starts listening for events.
4. **Termination**: `shutdown()` for all components.

# Plugin Development Guide

This documentation explains how to create and integrate plugins into the system. Plugins are the primary way to extend functionality. They allow adding new capabilities (e.g., input handling, AI, actions) without changing the core (Engine).

## Why Plugins?

- **Modularity**: Each plugin is independent and can be added/removed at runtime (hotswap).
- **Extensibility**: Subscribe to events via the event bus and publish your own.
- **Simplicity**: Inherit from `PluginBase` and implement 2-3 methods.

## Steps to Create a Plugin

1. **Create a File in the `/plugins/` Directory**:
    
    - File name: `<your_plugin_name>.py` (e.g., `my_input_plugin.py`).
    - The file must contain a class `Plugin` that inherits from `core.plugin_base.PluginBase`.
2. **Implement the Base Class**:

```Python
from core.plugin_base import PluginBase

class Plugin(PluginBase):
    def init(self, core):
        # Initialization: subscribe to events
        core.event_bus.subscribe('user_input', self.my_handler)
        # Available: core.event_bus, core.config, core.plugins (for interaction)

    def shutdown(self):
        # Cleanup: close resources, unsubscribe if needed
        pass

    # Your event handlers
    def my_handler(self, data):
        print(f"Handled data: {data}")
        # Publish a new event
        core.event_bus.publish('new_event', {'key': 'value'}, run_async=True)
```

## Best Practices: Managing Threads and Shared Resources

When developing plugins that use threads for tasks (e.g., stdin aka console input or network sockets), it is advisable to avoid duplication and conflicts for system stability.

**Why is this important?** Multiple threads competing for a single resource (e.g., `input()` from stdin) can lead to race conditions: data loss, errors, or unpredictable behavior.

### Recommendations and Example Code

1. **Check Within the Plugin**: Before starting a thread, verify if it already exists and is active (use `threading.Thread.is_alive()`).
2. **Global Coordination**: To prevent duplicates across plugins:
    - Publish an event (e.g., `'resource_handler_started'`) after starting.
    - Other plugins listen for this event and skip starting if it has already occurred.
    - Or use a flag in `core` (e.g., `core.is_input_active = True` after starting).
3. **Daemon Threads**: Set `thread.daemon = True` so threads terminate automatically on system shutdown.
4. **Cleanup in Shutdown**: Reset references to threads.

**Example Code for a Plugin with a Thread (Input Reading):**

```Python
import threading

class Plugin(PluginBase):
    def init(self, core):
        self.core = core
        self.my_thread = None  # Initialization

    def start_my_thread(self):
        # Check: Start only if it doesn't exist or isn't active
        if self.my_thread is None or not self.my_thread.is_alive():
            self.my_thread = threading.Thread(target=self.thread_function)
            self.my_thread.daemon = True
            self.my_thread.start()
            # Publish an event for global coordination
            self.core.event_bus.publish('handler_started', {'type': 'input'})
        else:
            # Log or publish a warning
            print("Thread already running; skipping.")

    def thread_function(self):
        while self.core.running:
            # Your logic (e.g., input())
            pass

    def shutdown(self):
        self.my_thread = None  # Reset reference (daemon will terminate itself)
```

---

Don't forget about protection, no one knows what AI will decide to do with your devices or you :3
