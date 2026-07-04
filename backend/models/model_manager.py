import threading
from typing import Dict, Any, Type

class ModelManager:
    _instance = None
    _lock = threading.Lock()
    _models: Dict[str, Any] = {}

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(ModelManager, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def get_model(self, model_name: str, model_class: Type) -> Any:
        """
        Gets a cached model instance by name. If not cached, it instantiates the model class,
        triggers load_model(), and caches the result.
        """
        if model_name not in self._models:
            with self._lock:
                if model_name not in self._models:
                    model_instance = model_class()
                    model_instance.load_model()
                    self._models[model_name] = model_instance
        return self._models[model_name]
