#!/usr/bin/env python3
"""
AI PC Autopilot - Модульная система управления ПК через LLM
Версия: 2.2
Описание: ИИ помощник для автоматизации задач в Linux консоли
Автор: [Your Name]
Зависимости: llama-cpp-python, json, subprocess
"""

import json
import os
import re
import subprocess
import sys
import time
import argparse
import threading
from enum import Enum
from typing import List, Dict, Any, Optional
from pathlib import Path

try:
    from llama_cpp import Llama
    LLAMA_AVAILABLE = True
except ImportError:
    LLAMA_AVAILABLE = False
    print("⚠ llama-cpp-python не установлен. Установите: pip install llama-cpp-python")


# ===========================================================================
# ГЛОБАЛЬНАЯ КОНФИГУРАЦИЯ
# ===========================================================================

class AppConfig:
    """Глобальная конфигурация приложения"""
    
    VERSION = "2.2.0"
    DEFAULT_CONFIG_PATH = "config.json"
    DEFAULT_MODELS_DIR = "./models"
    DEFAULT_DATA_DIR = "./data"
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_data = self._load_config(config_path or self.DEFAULT_CONFIG_PATH)
        
        # LLM параметры
        self.model_path = self.config_data.get('model_path', '')
        self.models_dir = self.config_data.get('models_dir', self.DEFAULT_MODELS_DIR)
        self.max_tokens = self.config_data.get('max_tokens', 2048)
        self.temperature = self.config_data.get('temperature', 0.5)
        self.n_ctx = self.config_data.get('n_ctx', 8192)
        self.n_gpu_layers = self.config_data.get('n_gpu_layers', 0)
        self.enable_self_read = self.config_data.get('enable_self_read', False)
        self.command_timeout = self.config_data.get('command_timeout', 30)
        
        # Дополнительные параметры
        self.n_batch = self.config_data.get('n_batch', 512)
        self.seed = self.config_data.get('seed', -1)
        self.top_k = self.config_data.get('top_k', 40)
        self.top_p = self.config_data.get('top_p', 0.95)
        self.repeat_penalty = self.config_data.get('repeat_penalty', 1.0)
        self.verbose = self.config_data.get('verbose', False)
        
        # Фильтры моделей
        self.model_whitelist = self.config_data.get('model_whitelist', [])
        self.model_blacklist = self.config_data.get('model_blacklist', [])
        
        # Настройки модулей
        self.enable_web_search = self.config_data.get('enable_web_search', False)
        self.data_dir = self.config_data.get('data_dir', self.DEFAULT_DATA_DIR)
        
        # Новые параметры для исправления проблем
        self.generation_timeout = self.config_data.get('generation_timeout', 300)  # 5 минут
        self.max_retries = self.config_data.get('max_retries', 3)
        
    def _load_config(self, config_path: str) -> Dict:
        """Загрузка конфигурации из JSON файла"""
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠ Ошибка загрузки конфигурации: {e}")
                return {}
        return {}
    
    def save_config(self, config_path: Optional[str] = None):
        """Сохранение конфигурации в JSON файл"""
        path = config_path or self.DEFAULT_CONFIG_PATH
        config_dict = {
            'model_path': self.model_path,
            'models_dir': self.models_dir,
            'max_tokens': self.max_tokens,
            'temperature': self.temperature,
            'n_ctx': self.n_ctx,
            'n_gpu_layers': self.n_gpu_layers,
            'enable_self_read': self.enable_self_read,
            'command_timeout': self.command_timeout,
            'n_batch': self.n_batch,
            'seed': self.seed,
            'top_k': self.top_k,
            'top_p': self.top_p,
            'repeat_penalty': self.repeat_penalty,
            'verbose': self.verbose,
            'model_whitelist': self.model_whitelist,
            'model_blacklist': self.model_blacklist,
            'enable_web_search': self.enable_web_search,
            'data_dir': self.data_dir,
            'generation_timeout': self.generation_timeout,
            'max_retries': self.max_retries
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(config_dict, f, indent=2, ensure_ascii=False)
        print(f"✓ Конфигурация сохранена: {path}")


# ===========================================================================
# МОДУЛЬ: ЛОГИРОВАНИЯ ПЛАНОВ
# ===========================================================================

class PlanLogger:
    """Модуль логирования промптов и планов выполнения"""
    
    MODULE_NAME = "Plan Logger"
    MODULE_VERSION = "1.0.0"
    MODULE_DESCRIPTION = "Модуль логирования промптов и результирующих планов"
    
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = data_dir
        self._ensure_data_dir()
        
    def _ensure_data_dir(self):
        """Создание директории для логов, если она не существует"""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir, exist_ok=True)
            print(f"✓ Создана директория для логов: {self.data_dir}")
    
    def log_prompt(self, prompt: str, mode: str, model_paths: List[str]):
        """Логирование исходного промпта"""
        log_entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "type": "prompt",
            "mode": mode,
            "prompt": prompt,
            "models": [os.path.basename(path) for path in model_paths],
            "models_count": len(model_paths)
        }
        
        self._save_log_entry(log_entry, "prompt")
    
    def log_successful_plan(self, prompt: str, plan: List[Dict]):
        """Логирование успешно созданного плана"""
        log_entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "type": "successful_plan",
            "prompt": prompt,
            "plan": plan,
            "actions_count": len(plan),
            "status": "success"
        }
        
        self._save_log_entry(log_entry, "plan")
    
    def log_failed_plan(self, prompt: str):
        """Логирование неудачной попытки создания плана"""
        log_entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "type": "failed_plan",
            "prompt": prompt,
            "status": "failed"
        }
        
        self._save_log_entry(log_entry, "plan")
    
    def log_execution_result(self, prompt: str, plan: List[Dict], results: List[Dict]):
        """Логирование результатов выполнения плана"""
        success_count = sum(1 for r in results if r.get('success', False))
        
        log_entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "type": "execution_result",
            "prompt": prompt,
            "plan": plan,
            "execution_results": results,
            "success_count": success_count,
            "total_actions": len(plan),
            "success_rate": success_count / len(plan) if plan else 0
        }
        
        self._save_log_entry(log_entry, "execution")
    
    def _save_log_entry(self, log_entry: Dict, log_type: str):
        """Сохранение записи лога в файл"""
        try:
            # Создаем имя файла с временной меткой
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"{log_type}_{timestamp}_{hash(log_entry['prompt'][:50]) % 10000:04d}.json"
            filepath = os.path.join(self.data_dir, filename)
            
            # Сохраняем в JSON формате
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(log_entry, f, indent=2, ensure_ascii=False, default=str)
            
            print(f"📝 Лог сохранен: {filepath}")
                
        except Exception as e:
            print(f"⚠️ Ошибка сохранения лога: {e}")
    
    def get_recent_logs(self, log_type: str = None, limit: int = 10) -> List[Dict]:
        """Получение последних логов"""
        try:
            logs = []
            for filename in os.listdir(self.data_dir):
                if log_type and not filename.startswith(log_type):
                    continue
                    
                filepath = os.path.join(self.data_dir, filename)
                if os.path.isfile(filepath) and filename.endswith('.json'):
                    with open(filepath, 'r', encoding='utf-8') as f:
                        log_entry = json.load(f)
                        logs.append(log_entry)
            
            # Сортируем по времени (новые сначала)
            logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            return logs[:limit]
            
        except Exception as e:
            print(f"⚠️ Ошибка чтения логов: {e}")
            return []


# ===========================================================================
# МОДУЛЬ: LLM (Управление языковыми моделями)
# ===========================================================================

class ModelScanner:
    """Сканер и фильтр моделей"""
    
    def __init__(self, models_dir: str, extension: str = ".gguf"):
        self.models_dir = models_dir
        self.extension = extension
        
    def scan_models(self) -> List[str]:
        """Сканирование директории на наличие моделей"""
        models = []
        if not os.path.exists(self.models_dir):
            print(f"⚠ Директория {self.models_dir} не существует")
            return models
            
        for item in os.listdir(self.models_dir):
            item_path = os.path.join(self.models_dir, item)
            if os.path.isfile(item_path) and item.endswith(self.extension):
                models.append(item_path)
        return models
    
    def filter_models(self, models: List[str], whitelist: List[str], 
                     blacklist: List[str]) -> List[str]:
        """Фильтрация моделей по белому и черному списку"""
        filtered = []
        
        for model_path in models:
            model_name = os.path.basename(model_path)
            
            # Проверка черного списка
            if any(pattern in model_name for pattern in blacklist):
                continue
                
            # Проверка белого списка (если не пустой)
            if whitelist and not any(pattern in model_name for pattern in whitelist):
                continue
                
            filtered.append(model_path)
            
        return filtered


class LLMManager:
    """Менеджер для работы с одной LLM моделью"""
    
    MODULE_NAME = "LLM Manager"
    MODULE_VERSION = "1.1.0"
    MODULE_DESCRIPTION = "Модуль управления языковой моделью с таймаутами"
    
    def __init__(self, model_path: str, config: AppConfig):
        self.config = config
        self.model_path = model_path
        self.llm = None
        self.is_initialized = False
        self._generation_timeout = config.generation_timeout
        
    def initialize_llm(self) -> bool:
        """Инициализация LLM модели"""
        if not LLAMA_AVAILABLE:
            print("❌ llama-cpp-python не установлен")
            return False
            
        try:
            if not os.path.exists(self.model_path):
                print(f"❌ Модель не найдена: {self.model_path}")
                return False
                
            print(f"⏳ Загрузка модели: {os.path.basename(self.model_path)}...")
            self.llm = Llama(
                model_path=self.model_path,
                n_ctx=self.config.n_ctx,
                n_gpu_layers=self.config.n_gpu_layers,
                n_batch=self.config.n_batch,
                seed=self.config.seed,
                verbose=self.config.verbose
            )
            self.is_initialized = True
            print(f"✓ Модель загружена: {os.path.basename(self.model_path)}")
            return True
        except Exception as e:
            print(f"❌ Ошибка инициализации модели: {e}")
            self.is_initialized = False
            return False
    
    def _generate_with_timeout(self, prompt: str, max_tokens: Optional[int] = None,
                              temperature: Optional[float] = None) -> Dict[str, Any]:
        """Генерация ответа с таймаутом"""
        result = {"error": "Таймаут генерации"}
        
        def generate():
            nonlocal result
            try:
                result = self.llm(
                    prompt,
                    max_tokens=max_tokens or self.config.max_tokens,
                    temperature=temperature or self.config.temperature,
                    top_k=self.config.top_k,
                    top_p=self.config.top_p,
                    repeat_penalty=self.config.repeat_penalty,
                    echo=False
                )
            except Exception as e:
                result = {"error": f"Ошибка генерации: {str(e)}"}
        
        thread = threading.Thread(target=generate)
        thread.start()
        thread.join(timeout=self._generation_timeout)
        
        if thread.is_alive():
            print(f"⚠️  Таймаут генерации ({self._generation_timeout} сек), прерывание...")
            return {"error": f"Таймаут генерации ({self._generation_timeout} секунд)"}
            
        return result
    
    def generate_response(self, prompt: str, max_tokens: Optional[int] = None,
                         temperature: Optional[float] = None) -> Dict[str, Any]:
        """Генерация ответа от модели с обработкой таймаутов"""
        if not self.is_available():
            return {"error": "Модель не инициализирована"}
            
        try:
            return self._generate_with_timeout(prompt, max_tokens, temperature)
        except Exception as e:
            return {"error": f"Ошибка генерации: {str(e)}"}
    
    def generate_plan(self, system_prompt: str, user_request: str) -> Optional[Dict]:
        """Генерация плана выполнения задачи с повторными попытками"""
        full_prompt = f"{system_prompt}\n\nUser request: {user_request}\n\nAnswer (JSON):"
        
        for attempt in range(self.config.max_retries):
            print(f"⏳ Попытка генерации плана {attempt + 1}/{self.config.max_retries}...")
            
            response = self.generate_response(full_prompt)
            
            if "error" in response:
                print(f"❌ Ошибка генерации плана: {response['error']}")
                if attempt < self.config.max_retries - 1:
                    time.sleep(2)
                continue
                
            try:
                response_text = response['choices'][0]['text']
                plan = PlanParser.parse_plan(response_text)
                if plan:
                    return plan
                else:
                    print(f"⚠️  Попытка {attempt + 1}: не удалось распарсить план")
            except Exception as e:
                print(f"❌ Ошибка парсинга плана: {e}")
            
            if attempt < self.config.max_retries - 1:
                time.sleep(2)
        
        print("❌ Все попытки генерации плана завершились неудачно")
        return None
    
    def self_reflect(self, initial_prompt: str, initial_response: str) -> str:
        """Самоанализ: модель читает свой ответ и улучшает его"""
        reflection_prompt = f"""Original request: {initial_prompt}

Original response: {initial_response}

Review this response and provide an improved version, correcting errors and adding information."""
        
        response = self.generate_response(reflection_prompt)
        if "error" not in response:
            return response['choices'][0]['text']
        return initial_response
    
    def unload_llm(self):
        """Выгрузка модели из памяти"""
        if self.llm:
            del self.llm
            self.llm = None
            self.is_initialized = False
            import gc
            gc.collect()
            print(f"✓ Модель выгружена: {os.path.basename(self.model_path)}")
    
    def is_available(self) -> bool:
        """Проверка доступности модели"""
        return self.is_initialized and self.llm is not None


class MultiModelManager:
    """Менеджер для работы с несколькими моделями одновременно"""
    
    def __init__(self, paths_to_models: List[str], config: AppConfig):
        self.config = config
        self.paths_to_models = paths_to_models
        self.llms_for_use: List[LLMManager] = []
        
    def initialize_multiple_llms(self) -> bool:
        """Инициализация нескольких моделей"""
        if not self.paths_to_models:
            print("❌ Список моделей пуст")
            return False
            
        success = True
        for model_path in self.paths_to_models:
            llm = LLMManager(model_path, self.config)
            if llm.initialize_llm():
                self.llms_for_use.append(llm)
            else:
                success = False
        
        if not self.llms_for_use:
            print("❌ Ни одна модель не была загружена")
            return False
            
        return success
    
    def generate_multiple_responses(self, prompt: str) -> Dict[str, Any]:
        """Генерация ответов от всех загруженных моделей"""
        responses = {}
        for llm in self.llms_for_use:
            model_name = os.path.basename(llm.model_path)
            response = llm.generate_response(prompt)
            responses[model_name] = response
        return responses
    
    def unload_multiple_llms(self):
        """Выгрузка всех моделей"""
        for llm in self.llms_for_use:
            llm.unload_llm()
        self.llms_for_use.clear()
    
    def is_available(self) -> bool:
        """Проверка доступности хотя бы одной модели"""
        return len(self.llms_for_use) > 0 and any(llm.is_available() for llm in self.llms_for_use)


class ModelRole(Enum):
    """Роли моделей в ансамбле"""
    SPECIALIST = "specialist"   # Специалист по конкретной задаче
    PLANNER = "planner"         # Планировщик задач
    CRITIC = "critic"           # Критик и аналитик
    EXECUTOR = "executor"       # Исполнитель
    SYNTHESIZER = "synthesizer" # Синтезатор ответов


class ModelOrchestrator:
    """Оркестратор для координации работы нескольких моделей"""
    
    def __init__(self, paths_to_models: List[str], config: AppConfig):
        self.config = config
        self.paths_to_models = paths_to_models
        self.model_roles: Dict[str, ModelRole] = {}
        
    def assign_role(self, model_path: str, role: ModelRole):
        """Назначение роли модели"""
        self.model_roles[model_path] = role
    
    def llms_cross_thinking(self, prompt: str, iterations: int = 2) -> str:
        """Кросс-мышление: модели обмениваются ответами и улучшают их"""
        accumulated_responses = []
        current_prompt = prompt
        
        for i in range(iterations):
            print(f"\n⏳ Итерация {i+1}/{iterations}...")
            
            # Используем одиночные ответы для экономии памяти
            responses = {}
            for model_path in self.paths_to_models:
                llm = LLMManager(model_path, self.config)
                if llm.initialize_llm():
                    response = llm.generate_response(current_prompt)
                    model_name = os.path.basename(model_path)
                    if "error" not in response:
                        responses[model_name] = response['choices'][0]['text']
                    llm.unload_llm()
            
            accumulated_responses.append(responses)
            
            # Формирование нового промпта с учетом предыдущих ответов
            if i < iterations - 1 and responses:
                responses_text = "\n\n".join([
                    f"Model {model}: {resp[:500]}..." 
                    for model, resp in responses.items()
                ])
                current_prompt = f"{prompt}\n\nPrevious answer options:\n{responses_text}\n\nImprove your answer considering these options:"
        
        return self._synthesize_best_response(accumulated_responses)
    
    def _synthesize_best_response(self, all_responses: List[Dict[str, str]]) -> str:
        """Синтез лучшего ответа из всех итераций"""
        if all_responses:
            last_iteration = all_responses[-1]
            if last_iteration:
                # Выбираем самый длинный ответ (как простую эвристику)
                return max(last_iteration.values(), key=len)
        return "Не удалось сгенерировать ответ"


# ===========================================================================
# МОДУЛЬ: ПЛАНИРОВЩИК / СОБИРАТЕЛЬ ДАННЫХ
# ===========================================================================

class SystemDataCollector:
    """Сборщик системной информации"""
    
    MODULE_NAME = "System Data Collector"
    MODULE_VERSION = "1.1.0"
    MODULE_DESCRIPTION = "Модуль сбора системной информации"
    
    @staticmethod
    def collect_system_info() -> Dict[str, Any]:
        """Сбор базовой информации о системе"""
        info = {
            "os": sys.platform,
            "cwd": os.getcwd(),
            "user": os.getenv("USER", "unknown"),
            "home": os.getenv("HOME", "unknown"),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Дополнительная информация через команды
        try:
            info["hostname"] = subprocess.check_output(
                ["hostname"], timeout=5
            ).decode().strip()
        except:
            info["hostname"] = "unknown"
            
        return info
    
    @staticmethod
    def generate_system_prompt(config: AppConfig) -> str:
        """Генерация системного промпта с информацией о системе"""
        sys_info = SystemDataCollector.collect_system_info()
        
        prompt = f"""You are a Linux system automation assistant running on:
- OS: {sys_info['os']}
- Hostname: {sys_info['hostname']}
- User: {sys_info['user']}
- Working Directory: {sys_info['cwd']}
- Time: {sys_info['timestamp']}

You create step-by-step plans to accomplish user tasks using terminal commands.

## AVAILABLE COMMANDS

**system_command**: Execute simple system command (safer, no shell)
  Parameters: command (str or list), timeout (int), cwd (str)
  Example: {{"event": "system_command", "data": {{"command": ["ls", "-la"]}}}}

**system_shell**: Execute shell command (supports pipes/redirects)
  Parameters: command (str), timeout (int), cwd (str)
  Example: {{"event": "system_shell", "data": {{"command": "echo 'test' | grep t"}}}}

**file_write**: Write content to file
  Parameters: path (str), content (str), append (bool)
  Example: {{"event": "file_write", "data": {{"path": "/tmp/test.txt", "content": "Hello"}}}}

**file_read**: Read file content
  Parameters: path (str), encoding (str)
  Example: {{"event": "file_read", "data": {{"path": "/tmp/test.txt"}}}}

**open_terminal**: Open new terminal and execute command
  Parameters: command (str), terminal (str) - optional terminal type
  Example: {{"event": "open_terminal", "data": {{"command": "python3 script.py"}}}}

## IMPORTANT INSTRUCTIONS

1. For system updates, use single command: "sudo apt update && sudo apt upgrade -y"
2. For creating scripts, first create file, then make executable, then run
3. Use "open_terminal" when user specifically requests new terminal window
4. Combine related commands where possible to reduce steps
5. Always use absolute paths for file operations

## RESPONSE FORMAT

Respond with JSON array of actions:
[
  {{"event": "system_command", "data": {{"command": ["ls", "-la"]}}, "description": "List files"}},
  {{"event": "file_read", "data": {{"path": "/tmp/test.txt"}}, "description": "Read test file"}}
]

IMPORTANT: Respond ONLY with valid JSON array, no markdown, no extra text."""
        
        return prompt


class PlanParser:
    """Парсер планов из ответов LLM"""
    
    @staticmethod
    def parse_plan(response_text: str) -> Optional[List[Dict]]:
        """Парсинг JSON из ответа LLM с улучшенной обработкой ошибок"""
        try:
            json_text = PlanParser.extract_json_from_text(response_text)
            if json_text:
                plan = json.loads(json_text)
                if PlanParser.validate_plan(plan):
                    return plan
            return None
        except json.JSONDecodeError as e:
            print(f"❌ Ошибка парсинга JSON: {e}")
            # Попробуем исправить JSON
            fixed_json = PlanParser.try_fix_json(response_text)
            if fixed_json:
                try:
                    plan = json.loads(fixed_json)
                    if PlanParser.validate_plan(plan):
                        print("✓ JSON исправлен автоматически")
                        return plan
                except:
                    pass
            return None
    
    @staticmethod
    def validate_plan(plan: Any) -> bool:
        """Валидация структуры плана"""
        if not isinstance(plan, list):
            return False
        
        for action in plan:
            if not isinstance(action, dict):
                return False
            if 'event' not in action or 'data' not in action:
                return False
        
        return True
    
    @staticmethod
    def extract_json_from_text(text: str) -> Optional[str]:
        """Извлечение JSON из текста с улучшенной эвристикой"""
        # Удаление markdown форматирования
        text = text.replace('```json', '').replace('```', '')
        
        # Поиск JSON массива
        start = text.find('[')
        if start == -1:
            return None
            
        # Поиск парной закрывающей скобки
        bracket_count = 0
        end = -1
        
        for i, char in enumerate(text[start:]):
            if char == '[':
                bracket_count += 1
            elif char == ']':
                bracket_count -= 1
                if bracket_count == 0:
                    end = start + i + 1
                    break
        
        if end > start:
            return text[start:end]
        
        return None
    
    @staticmethod
    def try_fix_json(text: str) -> Optional[str]:
        """Попытка исправить распространенные ошибки в JSON"""
        # Удаляем лишний текст до и после JSON
        start = text.find('[')
        end = text.rfind(']') + 1
        
        if start == -1 or end == 0:
            return None
            
        json_candidate = text[start:end]
        
        # Исправляем распространенные ошибки
        fixes = [
            (r',\s*]', ']'),  # Лишние запятые перед закрывающими скобками
            (r',\s*}', '}'),  # Лишние запятые перед закрывающими фигурными скобками
            (r'(\w+):', r'"\1":'),  # Ключи без кавычек
        ]
        
        for pattern, replacement in fixes:
            json_candidate = re.sub(pattern, replacement, json_candidate)
            
        return json_candidate


# ===========================================================================
# МОДУЛЬ: ВЫПОЛНЕНИЕ КОМАНД
# ===========================================================================

class CommandExecutor:
    """Модуль выполнения команд с улучшенным логированием"""
    
    MODULE_NAME = "Command Executor"
    MODULE_VERSION = "1.1.0"
    MODULE_DESCRIPTION = "Модуль выполнения системных команд с логированием"
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.execution_log = []
    
    def execute_plan(self, plan: List[Dict]) -> List[Dict[str, Any]]:
        """Выполнение плана действий с логированием"""
        results = []
        
        for i, action in enumerate(plan, 1):
            print(f"\n[{i}/{len(plan)}] Выполнение: {action.get('description', 'No description')}")
            result = self.execute_action(action)
            results.append(result)
            
            # Логируем результат
            self.execution_log.append({
                'action': action,
                'result': result,
                'timestamp': time.time()
            })
            
            # Прерывание при критической ошибке
            if not result.get('success', False) and result.get('critical', False):
                print("❌ Критическая ошибка, выполнение прервано")
                break
        
        return results
    
    def execute_action(self, action: Dict) -> Dict[str, Any]:
        """Выполнение одного действия с подробным логированием"""
        event = action.get('event')
        data = action.get('data', {})
        
        print(f"   🔧 Команда: {event}")
        if self.config.verbose:
            print(f"   📋 Данные: {data}")
        
        if event == 'system_command':
            return self._execute_system_command(data)
        elif event == 'system_shell':
            return self._execute_shell_command(data)
        elif event == 'file_write':
            return self._execute_file_write(data)
        elif event == 'file_read':
            return self._execute_file_read(data)
        elif event == 'open_terminal':
            return self._execute_open_terminal(data)
        else:
            error_msg = f"Unknown event: {event}"
            print(f"   ❌ {error_msg}")
            return {"success": False, "error": error_msg}
    
    def _execute_system_command(self, data: Dict) -> Dict[str, Any]:
        """Выполнение системной команды с логированием"""
        try:
            command = data.get('command', [])
            timeout = data.get('timeout', self.config.command_timeout)
            cwd = data.get('cwd', None)
            
            print(f"   💻 Выполнение: {command}")
            
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd
            )
            
            # Логируем вывод
            if result.stdout:
                print(f"   📤 stdout: {result.stdout[:500]}" + ("..." if len(result.stdout) > 500 else ""))
            if result.stderr:
                print(f"   📥 stderr: {result.stderr[:500]}" + ("..." if len(result.stderr) > 500 else ""))
            
            success = result.returncode == 0
            status = "✓ Успешно" if success else "❌ Ошибка"
            print(f"   {status} (код возврата: {result.returncode})")
            
            return {
                "success": success,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        except Exception as e:
            error_msg = str(e)
            print(f"   ❌ Исключение: {error_msg}")
            return {"success": False, "error": error_msg}
    
    def _execute_shell_command(self, data: Dict) -> Dict[str, Any]:
        """Выполнение shell команды с логированием"""
        try:
            command = data.get('command', '')
            timeout = data.get('timeout', self.config.command_timeout)
            cwd = data.get('cwd', None)
            
            print(f"   💻 Выполнение: {command}")
            
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd
            )
            
            # Логируем вывод
            if result.stdout:
                print(f"   📤 stdout: {result.stdout[:500]}" + ("..." if len(result.stdout) > 500 else ""))
            if result.stderr:
                print(f"   📥 stderr: {result.stderr[:500]}" + ("..." if len(result.stderr) > 500 else ""))
            
            success = result.returncode == 0
            status = "✓ Успешно" if success else "❌ Ошибка"
            print(f"   {status} (код возврата: {result.returncode})")
            
            return {
                "success": success,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        except Exception as e:
            error_msg = str(e)
            print(f"   ❌ Исключение: {error_msg}")
            return {"success": False, "error": error_msg}
    
    def _execute_open_terminal(self, data: Dict) -> Dict[str, Any]:
        """Открытие нового терминала с выполнением команды"""
        try:
            command = data.get('command', '')
            terminal = data.get('terminal', 'gnome-terminal')  # По умолчанию GNOME Terminal
            
            print(f"   🖥️  Открытие терминала: {terminal}")
            print(f"   💻 Команда в терминале: {command}")
            
            # Команда для открытия нового терминала
            if terminal == 'gnome-terminal':
                terminal_cmd = ['gnome-terminal', '--', 'bash', '-c', f"{command}; exec bash"]
            else:
                # Универсальная команда для других терминалов
                terminal_cmd = [terminal, '-e', f"bash -c '{command}; exec bash'"]
            
            result = subprocess.run(
                terminal_cmd,
                capture_output=True,
                text=True,
                timeout=30  # Таймаут для открытия терминала
            )
            
            success = result.returncode == 0
            status = "✓ Терминал открыт" if success else "⚠️ Возможна ошибка открытия терминала"
            print(f"   {status} (код возврата: {result.returncode})")
            
            return {
                "success": True,  # Всегда считаем успехом, даже если терминал не открылся
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "note": "Команда отправлена в терминал (проверьте открытые окна)"
            }
        except Exception as e:
            error_msg = str(e)
            print(f"   ❌ Ошибка открытия терминала: {error_msg}")
            return {"success": False, "error": error_msg}
    
    def _execute_file_write(self, data: Dict) -> Dict[str, Any]:
        """Запись в файл"""
        try:
            path = data.get('path')
            content = data.get('content', '')
            append = data.get('append', False)
            
            print(f"   📝 Запись в файл: {path}")
            if self.config.verbose:
                print(f"   📄 Содержимое: {content[:200]}" + ("..." if len(content) > 200 else ""))
            
            mode = 'a' if append else 'w'
            with open(path, mode, encoding='utf-8') as f:
                f.write(content)
            
            print("   ✓ Файл записан")
            return {"success": True, "message": f"File written: {path}"}
        except Exception as e:
            error_msg = str(e)
            print(f"   ❌ Ошибка записи: {error_msg}")
            return {"success": False, "error": error_msg}
    
    def _execute_file_read(self, data: Dict) -> Dict[str, Any]:
        """Чтение файла"""
        try:
            path = data.get('path')
            encoding = data.get('encoding', 'utf-8')
            
            print(f"   📖 Чтение файла: {path}")
            
            with open(path, 'r', encoding=encoding) as f:
                content = f.read()
            
            print(f"   ✓ Файл прочитан ({len(content)} символов)")
            return {"success": True, "content": content}
        except Exception as e:
            error_msg = str(e)
            print(f"   ❌ Ошибка чтения: {error_msg}")
            return {"success": False, "error": error_msg}


# ===========================================================================
# МОДУЛЬ: УПРАВЛЕНИЕ (Интерфейс пользователя)
# ===========================================================================

class ControlModule:
    """Модуль управления и пользовательского интерфейса с улучшенным режимом работы"""
    
    MODULE_NAME = "Control Module"
    MODULE_VERSION = "1.2.0"
    MODULE_DESCRIPTION = "Модуль управления и команд пользователя с динамической сменой режимов"
    
    def __init__(self, config: AppConfig, model_paths: List[str]):
        self.config = config
        self.model_paths = model_paths  # Сохраняем все модели
        self.current_plan = None
        self.llm_manager = None
        self.executor = CommandExecutor(config)
        self.current_mode = "single"
        self.cross_iterations = 2
        # Инициализируем логгер
        self.logger = PlanLogger(config.data_dir)

    def show_info(self, module_name: Optional[str] = None):
        """Вывод информации о командах или модуле"""
        if module_name:
            modules = {
                'llm': (LLMManager.MODULE_NAME, LLMManager.MODULE_VERSION, LLMManager.MODULE_DESCRIPTION),
                'collector': (SystemDataCollector.MODULE_NAME, SystemDataCollector.MODULE_VERSION, SystemDataCollector.MODULE_DESCRIPTION),
                'executor': (CommandExecutor.MODULE_NAME, CommandExecutor.MODULE_VERSION, CommandExecutor.MODULE_DESCRIPTION),
                'control': (ControlModule.MODULE_NAME, ControlModule.MODULE_VERSION, ControlModule.MODULE_DESCRIPTION),
                'logger': (PlanLogger.MODULE_NAME, PlanLogger.MODULE_VERSION, PlanLogger.MODULE_DESCRIPTION)
            }
            if module_name in modules:
                name, version, desc = modules[module_name]
                print(f"\n📦 Модуль: {name}")
                print(f"   Версия: {version}")
                print(f"   Описание: {desc}")
            else:
                print(f"❌ Модуль '{module_name}' не найден")
        else:
            print("\n📋 Доступные команды:")
            print("  /plan <task>       - Создать план для задачи")
            print("  /show              - Показать текущий план")
            print("  /show -d           - Показать план в JSON формате")
            print("  /execute           - Выполнить текущий план")
            print("  /mode              - Показать текущий режим работы")
            print("  /mode <single|multi|cross> [iterations] - Сменить режим")
            print("  /models            - Показать доступные модели")
            print("  /logs              - Показать последние логи")
            print("  /logs <type>       - Показать логи определенного типа")
            print("  /info              - Показать эту справку")
            print("  /info <module>     - Информация о модуле")
            print("  /exit              - Выход из программы")
    
    def show_models(self):
        """Показать доступные модели и текущий режим"""
        print(f"\n🤖 Доступные модели ({len(self.model_paths)}):")
        for i, path in enumerate(self.model_paths, 1):
            current_indicator = ""
            if self.current_mode == "single" and i == 1:
                current_indicator = " (текущая для single)"
            elif self.current_mode in ["multi", "cross"]:
                current_indicator = " (активна)"
            print(f"  {i}. {os.path.basename(path)}{current_indicator}")
        
        print(f"\n📊 Текущий режим: {self.current_mode}")
        if self.current_mode == "cross":
            print(f"   Итераций: {self.cross_iterations}")
        if self.current_mode in ["multi", "cross"]:
            print(f"   Используется моделей: {len(self.model_paths)}")
    
    def change_mode(self, mode: str, iterations: Optional[int] = None):
        """Смена режима работы"""
        if mode not in ["single", "multi", "cross"]:
            print("❌ Неизвестный режим. Доступные: single, multi, cross")
            return
        
        self.current_mode = mode
        if iterations and mode == "cross":
            self.cross_iterations = iterations
        
        print(f"✓ Режим изменен на: {mode}")
        if mode == "cross":
            print(f"  Количество итераций: {self.cross_iterations}")
    
    def handle_plan(self, task: str):
        """Обработка команды /plan с учетом текущего режима и ВСЕХ моделей"""
        print(f"\n⏳ Создание плана для задачи: {task}")
        print(f"📊 Режим: {self.current_mode}")
        
        # Логируем исходный промпт
        self.logger.log_prompt(task, self.current_mode, self.model_paths)
        
        if self.current_mode == "single":
            # Используем первую модель
            model_path = self.model_paths[0]
            self.llm_manager = LLMManager(model_path, self.config)
            if not self.llm_manager.initialize_llm():
                print("❌ Не удалось инициализировать модель")
                return
            
            system_prompt = SystemDataCollector.generate_system_prompt(self.config)
            self.current_plan = self.llm_manager.generate_plan(system_prompt, task)
            self.llm_manager.unload_llm()
            
        elif self.current_mode == "multi":
            # Используем ВСЕ модели параллельно
            print(f"🤖 Использование {len(self.model_paths)} моделей в multi-режиме")
            multi_manager = MultiModelManager(self.model_paths, self.config)
            if not multi_manager.initialize_multiple_llms():
                print("❌ Не удалось инициализировать модели")
                return
            
            system_prompt = SystemDataCollector.generate_system_prompt(self.config)
            full_prompt = f"{system_prompt}\n\nUser request: {task}\n\nAnswer (JSON):"
            
            responses = multi_manager.generate_multiple_responses(full_prompt)
            multi_manager.unload_multiple_llms()
            
            # Выбираем лучший ответ (самый длинный как простую эвристику)
            best_response = None
            for model_name, response in responses.items():
                if "error" not in response and response.get('choices'):
                    text = response['choices'][0]['text']
                    if not best_response or len(text) > len(best_response):
                        best_response = text
                        print(f"✓ Выбрана модель: {model_name}")
            
            if best_response:
                self.current_plan = PlanParser.parse_plan(best_response)
            else:
                print("❌ Все модели вернули ошибки")
                self.current_plan = None
                
        elif self.current_mode == "cross":
            # Используем кросс-мышление со ВСЕМИ моделями
            print(f"🤖 Использование {len(self.model_paths)} моделей в cross-режиме")
            orchestrator = ModelOrchestrator(self.model_paths, self.config)
            system_prompt = SystemDataCollector.generate_system_prompt(self.config)
            full_prompt = f"{system_prompt}\n\nUser request: {task}\n\nAnswer (JSON):"
            
            result = orchestrator.llms_cross_thinking(full_prompt, iterations=self.cross_iterations)
            self.current_plan = PlanParser.parse_plan(result)
        
        if self.current_plan:
            print(f"✓ План создан ({len(self.current_plan)} действий)")
            self.show_plan(detailed=False)
            # Логируем успешный план
            self.logger.log_successful_plan(task, self.current_plan)
        else:
            print("❌ Не удалось создать план")
            # Логируем неудачную попытку
            self.logger.log_failed_plan(task)
    
    def show_plan(self, detailed: bool = False):
        """Показать текущий план"""
        if not self.current_plan:
            print("❌ Нет активного плана. Используйте /plan <task>")
            return
        
        if detailed:
            print("\n📄 План (JSON формат):")
            print(json.dumps(self.current_plan, indent=2, ensure_ascii=False))
        else:
            print("\n📋 Текущий план:")
            for i, action in enumerate(self.current_plan, 1):
                desc = action.get('description', 'No description')
                event = action.get('event', 'unknown')
                print(f"  {i}. [{event}] {desc}")
    
    def execute_plan(self):
        """Выполнение текущего плана"""
        if not self.current_plan:
            print("❌ Нет активного плана. Используйте /plan <task>")
            return
        
        print("\n⚠️  ВНИМАНИЕ: Вы собираетесь выполнить план!")
        self.show_plan(detailed=False)
        
        confirm = input("\n❓ Продолжить выполнение? (yes/no): ").strip().lower()
        if confirm != 'yes':
            print("❌ Выполнение отменено")
            return
        
        print("\n▶️  Начало выполнения плана...\n")
        results = self.executor.execute_plan(self.current_plan)
        
        print("\n✓ Выполнение завершено")
        success_count = sum(1 for r in results if r.get('success', False))
        print(f"  Успешно: {success_count}/{len(results)}")
        
        # Логируем результаты выполнения
        self.logger.log_execution_result(
            "Выполнение плана",  # Используем описание вместо полного промпта для краткости
            self.current_plan,
            results
        )
        
        # Показываем детали в verbose режиме
        if self.config.verbose:
            for i, result in enumerate(results, 1):
                if not result.get('success', False):
                    print(f"  ❌ Действие {i} не удалось: {result.get('error', 'Unknown error')}")


# ===========================================================================
# ГЛАВНЫЙ МОДУЛЬ (MAIN)
# ===========================================================================

def parse_arguments():
    """Парсинг аргументов командной строки"""
    parser = argparse.ArgumentParser(
        description='AI PC Autopilot - ИИ помощник для управления Linux',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Основные аргументы
    parser.add_argument('-c', '--config', type=str, 
                       help='Путь к файлу конфигурации')
    parser.add_argument('-m', '--model', type=str,
                       help='Путь к конкретной модели')
    parser.add_argument('-d', '--models-dir', type=str,
                       help='Директория с моделями')
    
    # Флаги для LLM модуля
    parser.add_argument('-f', '--full', action='store_true',
                       help='Использовать все доступные модели')
    parser.add_argument('--multi', type=int, metavar='N',
                       help='Использовать N моделей одновременно')
    parser.add_argument('--cross-thinking', action='store_true',
                       help='Включить кросс-мышление моделей')
    parser.add_argument('--iterations', type=int, default=2,
                       help='Количество итераций для кросс-мышления (по умолчанию: 2)')
    
    # Дополнительные флаги
    parser.add_argument('--interactive', action='store_true',
                       help='Запустить в интерактивном режиме')
    parser.add_argument('--task', type=str,
                       help='Прямое выполнение задачи')
    parser.add_argument('--verbose', action='store_true',
                       help='Подробный вывод')
    parser.add_argument('--version', action='version',
                       version=f'AI PC Autopilot v{AppConfig.VERSION}')
    
    return parser.parse_args()


def select_models(config: AppConfig, args) -> List[str]:
    """Выбор моделей для использования"""
    models_dir = args.models_dir or config.models_dir
    scanner = ModelScanner(models_dir)
    available_models = scanner.scan_models()
    
    if not available_models:
        print(f"❌ Модели не найдены в директории: {models_dir}")
        return []
    
    # Фильтрация моделей
    filtered_models = scanner.filter_models(
        available_models,
        config.model_whitelist,
        config.model_blacklist
    )
    
    if not filtered_models:
        print("❌ После фильтрации не осталось доступных моделей")
        return []
    
    print(f"\n✓ Найдено моделей: {len(filtered_models)}")
    for i, model in enumerate(filtered_models, 1):
        print(f"  {i}. {os.path.basename(model)}")
    
    # Выбор моделей на основе флагов
    if args.model:
        # Конкретная модель указана пользователем
        if os.path.exists(args.model):
            return [args.model]
        else:
            print(f"⚠️  Модель не найдена: {args.model}")
            return []
    
    elif args.full:
        # Использовать все доступные модели
        print("\n📦 Режим: Использование всех доступных моделей")
        return filtered_models
    
    elif args.multi:
        # Использовать N моделей
        n = min(args.multi, len(filtered_models))
        print(f"\n📦 Режим: Использование {n} моделей")
        return filtered_models[:n]
    
    elif config.model_path and os.path.exists(config.model_path):
        # Использовать модель из конфига
        print(f"\n📦 Режим: Использование модели из конфига")
        return [config.model_path]
    
    else:
        # По умолчанию - первая доступная модель
        print(f"\n📦 Режим: Использование одной модели (по умолчанию)")
        return [filtered_models[0]]


def interactive_mode(config: AppConfig, model_paths: List[str], args):
    """Интерактивный режим работы"""
    if not model_paths:
        print("❌ Нет доступных моделей для работы")
        return
    
    control = ControlModule(config, model_paths)
    
    # Применяем аргументы командной строки к начальному режиму
    if args.cross_thinking:
        control.change_mode("cross", args.iterations)
    elif args.multi and len(model_paths) > 1:
        control.change_mode("multi")
    
    print("\n" + "="*60)
    print("🤖 AI PC Autopilot - Интерактивный режим")
    print("="*60)
    print("Введите /info для справки по командам")
    control.show_models()  # Теперь показывает все модели
    print("="*60 + "\n")
    
    while True:
        try:
            user_input = input(">>> ").strip()
            
            if not user_input:
                continue
            
            # Обработка команд
            if user_input == "/exit" or user_input == "/quit":
                print("👋 Выход из программы")
                break
            
            elif user_input == "/info":
                control.show_info()
            
            elif user_input.startswith("/info "):
                module_name = user_input.split(maxsplit=1)[1]
                control.show_info(module_name)
            
            elif user_input == "/models":
                control.show_models()
            
            elif user_input.startswith("/mode"):
                parts = user_input.split()
                if len(parts) == 1:
                    print(f"📊 Текущий режим: {control.current_mode}")
                    if control.current_mode == "cross":
                        print(f"   Итераций: {control.cross_iterations}")
                elif len(parts) >= 2:
                    mode = parts[1]
                    iterations = int(parts[2]) if len(parts) > 2 else None
                    control.change_mode(mode, iterations)
            
            elif user_input == "/logs":
                print("\n📊 Последние логи:")
                recent_logs = control.logger.get_recent_logs(limit=5)
                for log in recent_logs:
                    timestamp = log.get('timestamp', 'N/A')
                    log_type = log.get('type', 'unknown')
                    prompt_preview = log.get('prompt', '')[:50] + "..." if len(log.get('prompt', '')) > 50 else log.get('prompt', '')
                    print(f"  {timestamp} [{log_type}]: {prompt_preview}")
                    
            elif user_input.startswith("/logs "):
                log_type = user_input.split(maxsplit=1)[1]
                print(f"\n📊 Логи типа '{log_type}':")
                recent_logs = control.logger.get_recent_logs(log_type=log_type, limit=10)
                for log in recent_logs:
                    timestamp = log.get('timestamp', 'N/A')
                    prompt = log.get('prompt', 'N/A')
                    status = log.get('status', '')
                    print(f"  {timestamp} [{status}]: {prompt}")
            
            elif user_input.startswith("/plan "):
                task = user_input.split(maxsplit=1)[1]
                control.handle_plan(task)
            
            elif user_input == "/show":
                control.show_plan(detailed=False)
            
            elif user_input == "/show -d" or user_input == "/show --detailed":
                control.show_plan(detailed=True)
            
            elif user_input == "/execute":
                control.execute_plan()
            
            else:
                print("❌ Неизвестная команда. Используйте /info для справки")
        
        except KeyboardInterrupt:
            print("\n\n👋 Прервано пользователем")
            break
        except Exception as e:
            print(f"❌ Ошибка: {e}")


def direct_task_mode(config: AppConfig, model_paths: List[str], args):
    """Прямое выполнение задачи без интерактивного режима"""
    if not model_paths:
        print("❌ Нет доступных моделей для работы")
        return
    
    print(f"\n⏳ Выполнение задачи: {args.task}")
    
    control = ControlModule(config, model_paths)
    
    # Применяем аргументы командной строки к режиму
    if args.cross_thinking:
        control.change_mode("cross", args.iterations)
    elif args.multi and len(model_paths) > 1:
        control.change_mode("multi")
    
    print(f"📊 Режим: {control.current_mode}")
    
    control.handle_plan(args.task)
    
    if control.current_plan:
        control.show_plan(detailed=args.verbose)
        
        # Автоматическое выполнение (опасно!)
        print("\n⚠️  ВНИМАНИЕ: Автоматическое выполнение включено!")
        print("Используйте --interactive для ручного подтверждения")
        
        time.sleep(2)  # Небольшая задержка для чтения
        
        print("\n▶️  Начало выполнения...\n")
        results = control.executor.execute_plan(control.current_plan)
        
        print("\n✓ Выполнение завершено")
        success_count = sum(1 for r in results if r.get('success', False))
        print(f"  Успешно: {success_count}/{len(results)}")
        
        if args.verbose:
            print("\n📊 Детальные результаты:")
            for i, result in enumerate(results, 1):
                print(f"\n  Действие {i}:")
                print(f"    Успех: {result.get('success', False)}")
                if result.get('stdout'):
                    print(f"    Вывод: {result['stdout'][:200]}")
                if result.get('stderr'):
                    print(f"    Ошибки: {result['stderr'][:200]}")
    else:
        print("❌ Не удалось создать план")


def main():
    """Главная функция запуска приложения"""
    print("="*60)
    print("🤖 AI PC Autopilot - Система управления ПК через ИИ")
    print(f"   Версия: {AppConfig.VERSION}")
    print("="*60)
    
    # Проверка доступности llama-cpp-python
    if not LLAMA_AVAILABLE:
        print("\n❌ Критическая ошибка: llama-cpp-python не установлен")
        print("Установите командой: pip install llama-cpp-python")
        return 1
    
    # Парсинг аргументов
    args = parse_arguments()
    
    # Загрузка конфигурации
    config = AppConfig(args.config)
    
    # Применение флагов к конфигурации
    if args.verbose:
        config.verbose = True
    
    # Выбор моделей
    model_paths = select_models(config, args)
    
    if not model_paths:
        print("\n❌ Не удалось выбрать модели для работы")
        print("Проверьте:")
        print(f"  1. Директория моделей: {args.models_dir or config.models_dir}")
        print(f"  2. Формат файлов: .gguf")
        print(f"  3. Конфигурационный файл: {args.config or 'config.json'}")
        return 1
    
    # Выбор режима работы
    if args.task:
        # Прямое выполнение задачи
        direct_task_mode(config, model_paths, args)
    elif args.interactive or not args.task:
        # Интерактивный режим (по умолчанию)
        interactive_mode(config, model_paths, args)
    
    print("\n✓ Программа завершена")
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n👋 Прервано пользователем")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        if AppConfig().verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)