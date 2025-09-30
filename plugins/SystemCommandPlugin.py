import subprocess
import platform
import os
import json
from pathlib import Path
from core.plugin_base import PluginBase


class SystemCommandPlugin(PluginBase):
    def init(self, core):
        self.core = core
        self.os_type = platform.system()  # 'Windows', 'Linux', 'Darwin' (macOS)
        
        # Подписка на события
        core.event_bus.subscribe('system_command', self.handle_command)
        core.event_bus.subscribe('system_open', self.handle_open)
        core.event_bus.subscribe('system_launch', self.handle_launch)
        core.event_bus.subscribe('request_plugin_commands', self.publish_commands)
        core.event_bus.subscribe('system_shutdown', self.on_shutdown)
        
        # Загрузка безопасных команд из конфига
        self.load_safe_commands()
        
        self.core.event_bus.publish('output', f"💻 SystemCommandPlugin initialized (OS: {self.os_type})")

    def load_safe_commands(self):
        """Загрузка списка разрешенных команд"""
        config_path = Path("data/commands/system_safe_commands.json")
        
        # Дефолтные безопасные команды
        default_commands = {
            "Windows": {
                "notepad": "notepad.exe",
                "calculator": "calc.exe",
                "explorer": "explorer.exe",
                "cmd": "cmd.exe",
                "paint": "mspaint.exe"
            },
            "Linux": {
                "terminal": "gnome-terminal",
                "files": "nautilus",
                "editor": "gedit",
                "calculator": "gnome-calculator"
            },
            "Darwin": {
                "terminal": "open -a Terminal",
                "finder": "open -a Finder",
                "calculator": "open -a Calculator",
                "textedit": "open -a TextEdit"
            }
        }
        
        try:
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    self.safe_commands = json.load(f)
            else:
                self.safe_commands = default_commands
                # Сохраняем дефолтный конфиг
                config_path.parent.mkdir(parents=True, exist_ok=True)
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(default_commands, f, indent=2)
                self.core.event_bus.publish('output', 
                    f"Created default safe commands config at {config_path}")
        except Exception as e:
            self.core.event_bus.publish('output', f"Error loading safe commands: {e}")
            self.safe_commands = default_commands

    def publish_commands(self, data):
        """Публикация доступных команд для TaskPlanner"""
        commands = [
            {
                "event": "system_command",
                "description": "Execute a system command",
                "parameters": {
                    "command": "str - Command to execute",
                    "shell": "bool (optional) - Execute through shell (default: True)",
                    "timeout": "int (optional) - Timeout in seconds (default: 30)"
                },
                "example": {
                    "event": "system_command",
                    "data": {"command": "echo Hello", "shell": True}
                }
            },
            {
                "event": "system_open",
                "description": "Open a file or URL with default application",
                "parameters": {
                    "path": "str - File path or URL to open"
                },
                "example": {
                    "event": "system_open",
                    "data": {"path": "https://www.google.com"}
                }
            },
            {
                "event": "system_launch",
                "description": "Launch a predefined safe application",
                "parameters": {
                    "app": f"str - Application name. Available: {list(self.safe_commands.get(self.os_type, {}).keys())}"
                },
                "example": {
                    "event": "system_launch",
                    "data": {"app": "notepad"}
                }
            }
        ]
        
        self.core.event_bus.publish('plugin_commands_registered', {
            'plugin_name': 'system_command',
            'commands': commands
        })

    def handle_command(self, data):
        """Выполнение системной команды"""
        command = data.get('command', '')
        shell = data.get('shell', True)
        timeout = data.get('timeout', 30)
        
        if not command:
            self.core.event_bus.publish('output', "System command: no command provided")
            return
        
        try:
            self.core.event_bus.publish('output', f"Executing: {command}")
            
            result = subprocess.run(
                command,
                shell=shell,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                self.core.event_bus.publish('system_command_completed', {
                    'command': command,
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'returncode': result.returncode
                })
                
                if result.stdout:
                    self.core.event_bus.publish('output', f"Output: {result.stdout[:200]}")
            else:
                self.core.event_bus.publish('output', 
                    f"Command failed with code {result.returncode}: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            self.core.event_bus.publish('output', f"Command timeout after {timeout}s")
        except Exception as e:
            self.core.event_bus.publish('output', f"Command error: {e}")

    def handle_open(self, data):
        """Открытие файла или URL с помощью системного обработчика"""
        path = data.get('path', '')
        
        if not path:
            self.core.event_bus.publish('output', "System open: no path provided")
            return
        
        try:
            if self.os_type == 'Windows':
                os.startfile(path)
            elif self.os_type == 'Darwin':  # macOS
                subprocess.run(['open', path])
            else:  # Linux
                subprocess.run(['xdg-open', path])
            
            self.core.event_bus.publish('system_opened', {'path': path})
            self.core.event_bus.publish('output', f"Opened: {path}")
            
        except Exception as e:
            self.core.event_bus.publish('output', f"Open error: {e}")

    def handle_launch(self, data):
        """Запуск предопределенного приложения"""
        app = data.get('app', '').lower()
        
        if not app:
            self.core.event_bus.publish('output', "System launch: no app specified")
            return
        
        os_commands = self.safe_commands.get(self.os_type, {})
        
        if app not in os_commands:
            self.core.event_bus.publish('output', 
                f"Unknown app '{app}'. Available: {list(os_commands.keys())}")
            return
        
        command = os_commands[app]
        
        try:
            if self.os_type == 'Darwin' and command.startswith('open'):
                # macOS open command
                subprocess.Popen(command.split())
            else:
                subprocess.Popen(command, shell=True)
            
            self.core.event_bus.publish('system_launched', {'app': app, 'command': command})
            self.core.event_bus.publish('output', f"Launched: {app}")
            
        except Exception as e:
            self.core.event_bus.publish('output', f"Launch error: {e}")

    def on_shutdown(self, event_data):
        self.shutdown()

    def shutdown(self):
        """Очистка ресурсов"""
        self.core.event_bus.publish('output', "💻 SystemCommandPlugin shutdown")


# Для совместимости с загрузчиком
Plugin = SystemCommandPlugin
