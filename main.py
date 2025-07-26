import os
from core.engine import Engine

if __name__ == '__main__':
    config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    engine = Engine(config_path=config_path)
    engine.load_plugins()
    engine.run()