from core.plugin_base import PluginBase

class InputHandlerPlugin(PluginBase):
    def init(self, core):
        self.core = core
        self.last_plan = None
        core.event_bus.subscribe('user_input', self.handle_input)
        core.event_bus.subscribe('task_plan_generated', self.on_plan_generated)
        
        self.core.event_bus.publish('output', "InputHandlerPlugin: Type /help for task planner commands")

    def handle_input(self, user_input):
        # Обработка команд планировщика
        if user_input.startswith('/'):
            self.handle_task_commands(user_input)
            return
            
        # Существующая логика
        if not any([
            user_input.startswith('add '),
            user_input.startswith('rm '),
            user_input.startswith('remove '),
            user_input in ['exit', 'help', 'status']
        ]):
            self.core.event_bus.publish('user_message', {
                'text': user_input,
                'source': 'console'
            })

    def handle_task_commands(self, command):
        """Обработка команд для TaskPlanner"""
        parts = command.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if cmd == '/plan':
            if not args:
                self.core.event_bus.publish('output', "Usage: /plan <your request>")
                return
            
            self.core.event_bus.publish('task_plan_request', {
                'request': args,
                'auto_execute': False
            })
            
        elif cmd == '/execute':
            if self.last_plan:
                self.core.event_bus.publish('task_execute', {'plan': self.last_plan})
            else:
                self.core.event_bus.publish('output', "No plan to execute")
                
        elif cmd == '/show':
            if self.last_plan:
                self.show_plan()
            else:
                self.core.event_bus.publish('output', "No plan available")
                
        elif cmd == '/autoexec':
            if not args:
                self.core.event_bus.publish('output', "Usage: /autoexec <your request>")
                return
            
            self.core.event_bus.publish('task_plan_request', {
                'request': args,
                'auto_execute': True
            })
            
        elif cmd == '/help':
            self.show_help()
            
        else:
            self.core.event_bus.publish('output', f"Unknown command: {cmd}. Type /help for available commands.")

    def on_plan_generated(self, data):
        """Обработка сгенерированного плана"""
        self.last_plan = data.get('plan', [])
        request = data.get('request', '')
        
        self.core.event_bus.publish('output', f"✓ Plan generated for: '{request}' ({len(self.last_plan)} actions)")
        self.core.event_bus.publish('output', "Type /execute to run or /show to view")

    def show_plan(self):
        """Показать текущий план"""
        self.core.event_bus.publish('output', "\nCurrent plan:")
        for i, action in enumerate(self.last_plan, 1):
            desc = action.get('description', 'No description')
            event = action.get('event', 'unknown')
            self.core.event_bus.publish('output', f"  {i}. [{event}] {desc}")

    def show_help(self):
        """Показать справку по командам"""
        help_text = """
Task Planner Commands:
  /plan <request>     - Create task plan from natural language
  /execute            - Execute the last generated plan
  /show               - Show the current plan
  /autoexec <request> - Create and immediately execute plan
  /help               - Show this help

Examples:
  /plan open notepad and type hello
  /show
  /execute
  
  /autoexec click at 500 300
"""
        self.core.event_bus.publish('output', help_text)

Plugin = InputHandlerPlugin