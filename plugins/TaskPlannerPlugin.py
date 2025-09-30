import json
import os
from pathlib import Path
from core.plugin_base import PluginBase

# Импорт llama-cpp-python
try:
    from llama_cpp import Llama
    LLAMA_AVAILABLE = True
except ImportError:
    LLAMA_AVAILABLE = False
    print("Warning: llama-cpp-python not installed. Install with: pip install llama-cpp-python")


class TaskPlannerPlugin(PluginBase):
    def init(self, core):
        self.core = core
        self.llm = None
        self.available_commands = {}
        self.data_dir = Path("data")
        
        # Загружаем конфигурацию модели
        self.model_config = core.config.get('task_planner', {})
        self.model_path = self.model_config.get('model_path', 'models/model.gguf')
        self.max_tokens = self.model_config.get('max_tokens', 512)
        self.temperature = self.model_config.get('temperature', 0.7)
        self.n_ctx = self.model_config.get('n_ctx', 2048)
        self.n_gpu_layers = self.model_config.get('n_gpu_layers', 0)  # 0 = CPU only
        
        # Подписка на события
        core.event_bus.subscribe('task_plan_request', self.handle_plan_request)
        core.event_bus.subscribe('task_execute', self.handle_task_execute)
        core.event_bus.subscribe('plugin_commands_registered', self.register_plugin_commands)
        core.event_bus.subscribe('system_shutdown', self.on_shutdown)
        
        # Инициализация LLM
        if LLAMA_AVAILABLE:
            self.initialize_llm()
        
        # Загрузка доступных команд
        self.load_available_commands()
        
        # Запрос команд от других плагинов
        core.event_bus.publish('request_plugin_commands', {})
        
        self.core.event_bus.publish('output', "🧠 TaskPlannerPlugin initialized")

    def initialize_llm(self):
        """Инициализация LLM модели"""
        try:
            if not os.path.exists(self.model_path):
                self.core.event_bus.publish('output', 
                    f"⚠ Model file not found: {self.model_path}\n"
                    f"Please download a GGUF model and update config.json"
                )
                return
            
            self.core.event_bus.publish('output', f"Loading LLM model from {self.model_path}...")
            
            self.llm = Llama(
                model_path=self.model_path,
                n_ctx=self.n_ctx,
                n_gpu_layers=self.n_gpu_layers,
                verbose=False
            )
            
            self.core.event_bus.publish('output', "✓ LLM model loaded successfully")
            
        except Exception as e:
            self.core.event_bus.publish('output', f"❌ Failed to load LLM: {e}")
            self.llm = None

    def load_available_commands(self):
        """Загрузка описаний команд из data/commands/"""
        commands_dir = self.data_dir / "commands"
        
        if not commands_dir.exists():
            commands_dir.mkdir(parents=True, exist_ok=True)
            self.core.event_bus.publish('output', f"Created commands directory: {commands_dir}")
            return
        
        # Загружаем все JSON файлы с командами
        for command_file in commands_dir.glob("*.json"):
            try:
                with open(command_file, 'r', encoding='utf-8') as f:
                    commands = json.load(f)
                    plugin_name = command_file.stem
                    self.available_commands[plugin_name] = commands
                    self.core.event_bus.publish('output', 
                        f"Loaded {len(commands)} commands from {plugin_name}")
            except Exception as e:
                self.core.event_bus.publish('output', 
                    f"Error loading {command_file}: {e}")

    def register_plugin_commands(self, data):
        """Регистрация команд от плагинов"""
        plugin_name = data.get('plugin_name')
        commands = data.get('commands', [])
        
        if plugin_name and commands:
            self.available_commands[plugin_name] = commands
            self.core.event_bus.publish('output', 
                f"Registered {len(commands)} commands from {plugin_name}")

    def generate_system_prompt(self):
        """Генерация системного промпта с доступными командами"""
        commands_desc = []
        
        for plugin_name, commands in self.available_commands.items():
            commands_desc.append(f"\n{plugin_name.upper()} COMMANDS:")
            for cmd in commands:
                event = cmd.get('event', '')
                desc = cmd.get('description', '')
                params = cmd.get('parameters', {})
                
                params_str = ', '.join([f"{k}: {v}" for k, v in params.items()])
                commands_desc.append(f"  - {event}: {desc}")
                if params_str:
                    commands_desc.append(f"    Parameters: {params_str}")
        
        system_prompt = f"""You are a task planning assistant. Your job is to break down user requests into a sequence of executable actions.

AVAILABLE COMMANDS:
{''.join(commands_desc)}

RESPONSE FORMAT:
You must respond with a valid JSON array of actions. Each action has:
- "event": the event name to publish
- "data": object with parameters for the event
- "description": brief description of what this action does

Example response:
[
  {{"event": "mouse_move", "data": {{"x": 500, "y": 300}}, "description": "Move mouse to center"}},
  {{"event": "mouse_click", "data": {{"button": "left", "clicks": 1}}, "description": "Click left button"}},
  {{"event": "keyboard_type", "data": {{"text": "Hello"}}, "description": "Type greeting"}}
]

IMPORTANT RULES:
1. Respond ONLY with the JSON array, no additional text
2. Use only the commands listed above
3. Break complex tasks into simple steps
4. Be specific with coordinates and parameters
5. Consider the logical order of actions"""

        return system_prompt

    def handle_plan_request(self, data):
        """Обработка запроса на планирование задачи"""
        if not LLAMA_AVAILABLE or not self.llm:
            self.core.event_bus.publish('output', 
                "❌ LLM not available. Cannot plan tasks.")
            return
        
        user_request = data.get('request', '')
        
        if not user_request:
            self.core.event_bus.publish('output', "No request provided for planning")
            return
        
        self.core.event_bus.publish('output', f"🤔 Planning task: {user_request}")
        
        try:
            # Генерация плана
            system_prompt = self.generate_system_prompt()
            full_prompt = f"{system_prompt}\n\nUSER REQUEST: {user_request}\n\nRESPONSE:"
            
            response = self.llm(
                full_prompt,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                stop=["USER REQUEST:", "\n\n\n"],
                echo=False
            )
            
            response_text = response['choices'][0]['text'].strip()
            
            # Парсинг JSON ответа
            plan = self.parse_plan(response_text)
            
            if plan:
                self.core.event_bus.publish('task_plan_generated', {
                    'request': user_request,
                    'plan': plan,
                    'raw_response': response_text
                })
                
                self.core.event_bus.publish('output', 
                    f"✓ Generated plan with {len(plan)} actions")
                
                # Опционально: сразу выполнить план
                if data.get('auto_execute', False):
                    self.execute_plan(plan)
            else:
                self.core.event_bus.publish('output', 
                    f"❌ Failed to parse plan. Raw response:\n{response_text}")
                
        except Exception as e:
            self.core.event_bus.publish('output', f"❌ Planning error: {e}")

    def parse_plan(self, response_text):
        """Парсинг JSON плана из ответа LLM"""
        try:
            # Попытка найти JSON массив в ответе
            start = response_text.find('[')
            end = response_text.rfind(']') + 1
            
            if start != -1 and end > start:
                json_str = response_text[start:end]
                plan = json.loads(json_str)
                
                # Валидация структуры
                if isinstance(plan, list):
                    for action in plan:
                        if not all(k in action for k in ['event', 'data']):
                            return None
                    return plan
            
            return None
            
        except json.JSONDecodeError as e:
            self.core.event_bus.publish('output', f"JSON parse error: {e}")
            return None

    def handle_task_execute(self, data):
        """Выполнение готового плана"""
        plan = data.get('plan', [])
        
        if not plan:
            self.core.event_bus.publish('output', "No plan provided for execution")
            return
        
        self.execute_plan(plan)

    def execute_plan(self, plan):
        """Последовательное выполнение плана"""
        self.core.event_bus.publish('output', f"▶ Executing plan with {len(plan)} actions...")
        
        for i, action in enumerate(plan, 1):
            event = action.get('event')
            event_data = action.get('data', {})
            description = action.get('description', 'No description')
            
            self.core.event_bus.publish('output', 
                f"  [{i}/{len(plan)}] {description}")
            
            # Публикуем событие для выполнения
            self.core.event_bus.publish(event, event_data)
            
            # Небольшая задержка между действиями
            import time
            time.sleep(0.1)
        
        self.core.event_bus.publish('task_plan_completed', {'actions_count': len(plan)})
        self.core.event_bus.publish('output', "✓ Plan execution completed")

    def on_shutdown(self, event_data):
        self.shutdown()

    def shutdown(self):
        """Очистка ресурсов"""
        if self.llm:
            del self.llm
            self.llm = None
        self.core.event_bus.publish('output', "🧠 TaskPlannerPlugin shutdown")


# Для совместимости с загрузчиком
Plugin = TaskPlannerPlugin
