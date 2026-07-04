from typing import Dict, Any
from backend.models.model_manager import ModelManager
from backend.models.detector_model import DetectorModel

def run_detector_inference(text: str) -> Dict[str, Any]:
    """
    Retrieves the singleton DetectorModel from ModelManager and performs prediction.
    """
    manager = ModelManager()
    model = manager.get_model("detector", DetectorModel)
    return model.predict(text)
