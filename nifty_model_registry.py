# nifty_model_registry.py
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

class BackendType(Enum):
    LOCAL_OLLAMA = "local_ollama"
    CLOUD_DEEPSEEK = "cloud_deepseek"
    LOCAL_LLAMA = "local_llama"
    LOCAL_MISTRAL = "local_mistral"

@dataclass
class ModelConfig:
    """Configuration for a single AI model"""
    name: str
    backend_type: BackendType
    model_name: str
    enabled: bool
    display_name: str
    description: str
    execution_order: int
    parameters: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model config to dictionary"""
        return {
            "name": self.name,
            "backend_type": self.backend_type.value,
            "model_name": self.model_name,
            "enabled": self.enabled,
            "display_name": self.display_name,
            "description": self.description,
            "execution_order": self.execution_order,
            "parameters": self.parameters
        }

class ModelRegistry:
    """Registry for managing multiple AI models"""
    
    def __init__(self):
        self.models: Dict[str, ModelConfig] = {}
        self._initialize_default_models()
    
    def _initialize_default_models(self):
        """Initialize with default model configurations"""
        default_models = [
            ModelConfig(
                name="deepseek_r1",
                backend_type=BackendType.LOCAL_OLLAMA,
                model_name="deepseek-r1:latest",
                enabled=True,
                display_name="🧠 DeepSeek R1",
                description="Local DeepSeek R1 model via Ollama",
                execution_order=1,
                parameters={
                    "temperature": 0.1,
                    "top_p": 1.0,
                    "max_tokens": 1200,
                    "timeout": 600
                }
            ),
            ModelConfig(
                name="cloud_deepseek",
                backend_type=BackendType.CLOUD_DEEPSEEK,
                model_name="deepseek-chat",
                enabled=False,
                display_name="☁️ DeepSeek Cloud",
                description="Cloud DeepSeek API",
                execution_order=2,
                parameters={
                    "temperature": 0,
                    "top_p": 1.0,
                    "max_tokens": 1200,
                    "timeout": 300
                }
            ),
            ModelConfig(
                name="llama3",
                backend_type=BackendType.LOCAL_LLAMA,
                model_name="llama3:latest",
                enabled=False,
                display_name="🦙 Llama 3",
                description="Local Llama 3 model via Ollama",
                execution_order=3,
                parameters={
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "max_tokens": 1000,
                    "timeout": 600
                }
            ),
            ModelConfig(
                name="mistral",
                backend_type=BackendType.LOCAL_MISTRAL,
                model_name="mistral:latest",
                enabled=False,
                display_name="🌪️ Mistral",
                description="Local Mistral model via Ollama",
                execution_order=4,
                parameters={
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "max_tokens": 1000,
                    "timeout": 600
                }
            )
        ]
        
        for model in default_models:
            self.models[model.name] = model
    
    def get_model(self, model_name: str) -> Optional[ModelConfig]:
        """Get model configuration by name"""
        return self.models.get(model_name)
    
    def get_enabled_models(self) -> List[ModelConfig]:
        """Get all enabled models (unordered)"""
        return [model for model in self.models.values() if model.enabled]
    
    def get_enabled_models_in_order(self) -> List[ModelConfig]:
        """Get enabled models sorted by execution order"""
        enabled_models = self.get_enabled_models()
        return sorted(enabled_models, key=lambda x: x.execution_order)
    
    def get_all_models(self) -> List[ModelConfig]:
        """Get all models regardless of enabled status"""
        return list(self.models.values())
    
    def get_all_models_in_order(self) -> List[ModelConfig]:
        """Get all models sorted by execution order"""
        return sorted(self.models.values(), key=lambda x: x.execution_order)
    
    def enable_model(self, model_name: str) -> bool:
        """Enable a specific model"""
        model = self.get_model(model_name)
        if model:
            model.enabled = True
            return True
        return False
    
    def disable_model(self, model_name: str) -> bool:
        """Disable a specific model"""
        model = self.get_model(model_name)
        if model:
            model.enabled = False
            return True
        return False
    
    def set_model_enabled(self, model_name: str, enabled: bool) -> bool:
        """Set enabled status for a model"""
        model = self.get_model(model_name)
        if model:
            model.enabled = enabled
            return True
        return False
    
    def update_model_parameter(self, model_name: str, param_name: str, param_value: Any) -> bool:
        """Update a parameter for a specific model"""
        model = self.get_model(model_name)
        if model and param_name in model.parameters:
            model.parameters[param_name] = param_value
            return True
        return False
    
    def update_execution_order(self, model_name: str, new_order: int) -> bool:
        """Update execution order for a model"""
        model = self.get_model(model_name)
        if model:
            model.execution_order = new_order
            return True
        return False
    
    def add_model(self, model_config: ModelConfig) -> bool:
        """Add a new model to the registry"""
        if model_config.name in self.models:
            return False  # Model already exists
        
        self.models[model_config.name] = model_config
        return True
    
    def remove_model(self, model_name: str) -> bool:
        """Remove a model from the registry"""
        if model_name in self.models:
            del self.models[model_name]
            return True
        return False
    
    def get_model_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all models"""
        status = {}
        for model_name, model in self.models.items():
            status[model_name] = {
                "enabled": model.enabled,
                "execution_order": model.execution_order,
                "display_name": model.display_name,
                "backend_type": model.backend_type.value,
                "parameters": model.parameters
            }
        return status
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert entire registry to dictionary"""
        return {
            "models": {name: model.to_dict() for name, model in self.models.items()}
        }
    
    def from_dict(self, config_dict: Dict[str, Any]) -> bool:
        """Load registry configuration from dictionary"""
        try:
            models_data = config_dict.get("models", {})
            
            for model_name, model_data in models_data.items():
                if model_name in self.models:
                    # Update existing model
                    model = self.models[model_name]
                    model.enabled = model_data.get("enabled", model.enabled)
                    model.execution_order = model_data.get("execution_order", model.execution_order)
                    model.parameters.update(model_data.get("parameters", {}))
            
            return True
        except Exception:
            return False


# Global registry instance
model_registry = ModelRegistry()

def test_model_registry():
    """Test function for model registry"""
    registry = ModelRegistry()
    
    print("=== Model Registry Test ===")
    print(f"Total models: {len(registry.get_all_models())}")
    print(f"Enabled models: {len(registry.get_enabled_models())}")
    
    print("\nAll models in execution order:")
    for model in registry.get_all_models_in_order():
        status = "✅ ENABLED" if model.enabled else "❌ DISABLED"
        print(f"  {model.execution_order}. {model.display_name} ({model.name}) - {status}")
    
    print("\nEnabled models in execution order:")
    for model in registry.get_enabled_models_in_order():
        print(f"  {model.execution_order}. {model.display_name}")
    
    # Test enabling/disabling
    print("\n=== Testing Enable/Disable ===")
    registry.enable_model("llama3")
    registry.disable_model("deepseek_r1")
    
    print("After changes:")
    for model in registry.get_all_models_in_order():
        status = "✅ ENABLED" if model.enabled else "❌ DISABLED"
        print(f"  {model.execution_order}. {model.display_name} - {status}")
    
    print("\nModel status:")
    print(registry.get_model_status())

if __name__ == "__main__":
    test_model_registry()