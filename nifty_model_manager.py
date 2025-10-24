# nifty_model_manager.py
import asyncio
import time
import json
from typing import List, Dict, Any, Optional
from nifty_model_registry import ModelRegistry, ModelConfig

class ModelManager:
    def __init__(self, websocket_multiplexer=None):
        self.registry = ModelRegistry()
        self.websocket_multiplexer = websocket_multiplexer
        self.current_execution_id = None
        self.is_running = False
        
    async def execute_models_sequential(self, 
                                      oi_data: List[Dict[str, Any]],
                                      oi_pcr: float,
                                      volume_pcr: float, 
                                      current_nifty: float,
                                      expiry_date: str,
                                      stock_data: Optional[Dict[str, Any]] = None,
                                      banknifty_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute all enabled models in sequential order
        Returns aggregated results from all models
        """
        if self.is_running:
            await self._broadcast_message("error", "Model execution already in progress")
            return {"status": "error", "message": "Execution already running"}
            
        self.is_running = True
        self.current_execution_id = f"exec_{int(time.time())}"
        all_results = {}
        
        try:
            # Get enabled models in execution order
            enabled_models = self.registry.get_enabled_models_in_order()
            
            if not enabled_models:
                await self._broadcast_message("error", "No models enabled for execution")
                return {"status": "error", "message": "No models enabled"}
                
            await self._broadcast_message("status", f"Starting sequential execution of {len(enabled_models)} models")
            
            # Execute each model sequentially
            for model_config in enabled_models:
                if not self.is_running:  # Check if stopped
                    break
                    
                model_name = model_config.name
                await self._broadcast_message("status", f"Executing {model_name}...")
                
                try:
                    # Execute single model
                    result = await self._execute_single_model(
                        model_config, 
                        oi_data, oi_pcr, volume_pcr, current_nifty, expiry_date,
                        stock_data, banknifty_data
                    )
                    
                    all_results[model_name] = result
                    await self._broadcast_model_result(model_name, result)
                    
                except Exception as e:
                    error_msg = f"Model {model_name} failed: {str(e)}"
                    await self._broadcast_model_error(model_name, error_msg)
                    all_results[model_name] = {"status": "error", "error": error_msg}
                    
                    # Continue with next model even if one fails
                    continue
                    
            await self._broadcast_message("status", "Model execution completed")
            return {
                "status": "success", 
                "execution_id": self.current_execution_id,
                "results": all_results
            }
            
        except Exception as e:
            error_msg = f"Model execution failed: {str(e)}"
            await self._broadcast_message("error", error_msg)
            return {"status": "error", "error": error_msg}
            
        finally:
            self.is_running = False
            
    async def _execute_single_model(self,
                                  model_config: ModelConfig,
                                  oi_data: List[Dict[str, Any]],
                                  oi_pcr: float,
                                  volume_pcr: float,
                                  current_nifty: float,
                                  expiry_date: str,
                                  stock_data: Optional[Dict[str, Any]] = None,
                                  banknifty_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute a single model based on its configuration
        """
        model_name = model_config.name
        
        # Broadcast start of this model
        await self._broadcast_model_status(model_name, "started")
        
        try:
            # Import and initialize the appropriate analyzer based on model type
            if model_config.backend_type == "local_ollama":
                from nifty_ai_analyzer import NiftyAIAnalyzer
                analyzer = NiftyAIAnalyzer()
                analyzer.local_ai_enabled = True
                analyzer.ollama_model = model_config.model_name
                
                # Execute analysis
                analysis_result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: analyzer.get_ai_analysis(
                        oi_data=oi_data,
                        oi_pcr=oi_pcr,
                        volume_pcr=volume_pcr,
                        current_nifty=current_nifty,
                        expiry_date=expiry_date,
                        stock_data=stock_data,
                        banknifty_data=banknifty_data
                    )
                )
                
                result = {
                    "status": "success",
                    "model": model_name,
                    "analysis": analysis_result,
                    "execution_time": time.time(),
                    "backend": "local_ollama"
                }
                
            elif model_config.backend_type == "cloud_deepseek":
                from nifty_ai_analyzer import NiftyAIAnalyzer
                analyzer = NiftyAIAnalyzer()
                analyzer.local_ai_enabled = False
                
                # Execute analysis
                analysis_result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: analyzer.get_ai_analysis(
                        oi_data=oi_data,
                        oi_pcr=oi_pcr,
                        volume_pcr=volume_pcr,
                        current_nifty=current_nifty,
                        expiry_date=expiry_date,
                        stock_data=stock_data,
                        banknifty_data=banknifty_data
                    )
                )
                
                result = {
                    "status": "success", 
                    "model": model_name,
                    "analysis": analysis_result,
                    "execution_time": time.time(),
                    "backend": "cloud_deepseek"
                }
                
            else:
                raise ValueError(f"Unsupported backend type: {model_config.backend_type}")
                
            await self._broadcast_model_status(model_name, "completed")
            return result
            
        except Exception as e:
            await self._broadcast_model_status(model_name, "failed")
            raise e
            
    async def stop_execution(self):
        """Stop current model execution"""
        if self.is_running:
            self.is_running = False
            await self._broadcast_message("status", "Model execution stopped by user")
            return True
        return False
        
    async def _broadcast_message(self, message_type: str, message: str):
        """Broadcast general message"""
        if self.websocket_multiplexer:
            await self.websocket_multiplexer.broadcast_message(message_type, message)
            
    async def _broadcast_model_status(self, model_name: str, status: str):
        """Broadcast model-specific status"""
        if self.websocket_multiplexer:
            await self.websocket_multiplexer.broadcast_model_status(model_name, status)
            
    async def _broadcast_model_result(self, model_name: str, result: Dict[str, Any]):
        """Broadcast model result"""
        if self.websocket_multiplexer:
            await self.websocket_multiplexer.broadcast_model_result(model_name, result)
            
    async def _broadcast_model_error(self, model_name: str, error: str):
        """Broadcast model error"""
        if self.websocket_multiplexer:
            await self.websocket_multiplexer.broadcast_model_error(model_name, error)
            
    def get_execution_status(self) -> Dict[str, Any]:
        """Get current execution status"""
        return {
            "is_running": self.is_running,
            "execution_id": self.current_execution_id,
            "enabled_models": [model.name for model in self.registry.get_enabled_models_in_order()]
        }


# Singleton instance for easy access
model_manager = ModelManager()

async def test_model_manager():
    """Test function for model manager"""
    manager = ModelManager()
    
    # Test data
    test_data = {
        "oi_data": [],
        "oi_pcr": 1.0,
        "volume_pcr": 1.0, 
        "current_nifty": 22000.0,
        "expiry_date": "25-DEC-2024",
        "stock_data": None,
        "banknifty_data": None
    }
    
    print("Testing Model Manager...")
    results = await manager.execute_models_sequential(**test_data)
    print(f"Execution results: {results}")

if __name__ == "__main__":
    asyncio.run(test_model_manager())