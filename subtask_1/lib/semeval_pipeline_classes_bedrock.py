"""
SemEval 2026 Task 11 - Pipeline Classes (Bedrock Version)
Refactored to use AWS Bedrock instead of HuggingFace models
"""

import os
import json
import math
import time
import glob
import re
import subprocess
import zipfile
import traceback
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, asdict

from bedrock_client import BedrockClient


@dataclass
class Config:
    """Configuration for SemEval Task 11 Pipeline with Bedrock"""
    
    # Directories
    save_dir: str = "./semeval_models"
    results_dir: str = "./semeval_results"
    
    # Bedrock settings
    model_id: str = "qwen.qwen3-32b-v1:0"  # Bedrock model ID
    region_name: str = "us-east-1"
    bearer_token: str = None  # Optional, can use env var
    
    # Training/Test settings
    num_training: int = 20
    num_test: int = 0  # 0 = use all test data
    
    # Inference settings
    batch_size: int = 4
    max_new_tokens: int = 512
    temperature: float = 0.7
    top_k: int = 20
    
    # Data URLs
    train_data_url: str = "https://raw.githubusercontent.com/neuro-symbolic-ai/semeval_2026_task_11/refs/heads/main/train_data/subtask%201/train_data.json"
    test_data_url: str = "https://raw.githubusercontent.com/neuro-symbolic-ai/semeval_2026_task_11/refs/heads/main/test_data/subtask%201/test_data_subtask_1.json"
    
    def create_directories(self):
        """Create necessary directories"""
        os.makedirs(self.save_dir, exist_ok=True)
        os.makedirs(self.results_dir, exist_ok=True)
        print(f"✓ Directories created")
    
    def to_dict(self) -> Dict:
        """Export config as dictionary"""
        config_dict = asdict(self)
        # Don't expose bearer token in dict
        if 'bearer_token' in config_dict:
            config_dict['bearer_token'] = '***' if config_dict['bearer_token'] else None
        return config_dict


class DataLoader:
    """Load and manage training/test data"""
    
    def __init__(self, config: Config):
        self.config = config
        self.train_data = None
        self.test_data = None
    
    def download_data(self, url: str, filepath: str):
        """Download data from URL"""
        if not os.path.exists(filepath):
            print(f"Downloading from {url}...")
            import urllib.request
            urllib.request.urlretrieve(url, filepath)
            print(f"✓ Downloaded to {filepath}")
        else:
            print(f"✓ Data exists at {filepath}")
        return filepath
    
    def load_train_data(self) -> List[Dict]:
        """Load training data"""
        os.makedirs('./train_data', exist_ok=True)
        filepath = './train_data/train_data.json'
        self.download_data(self.config.train_data_url, filepath)
        
        with open(filepath, 'r') as f:
            self.train_data = json.load(f)
        print(f"✓ Loaded {len(self.train_data)} training examples")
        return self.train_data
    
    def load_test_data(self) -> List[Dict]:
        """Load test data"""
        os.makedirs('./test_data', exist_ok=True)
        filepath = './test_data/test_data_subtask_1.json'
        self.download_data(self.config.test_data_url, filepath)
        
        with open(filepath, 'r') as f:
            self.test_data = json.load(f)
        print(f"✓ Loaded {len(self.test_data)} test examples")
        return self.test_data
    
    def get_train_subset(self, n: int = None) -> List[Dict]:
        """Get subset of training data"""
        if self.train_data is None:
            self.load_train_data()
        n = n or self.config.num_training
        return self.train_data[:n] if n > 0 else []
    
    def get_test_subset(self, n: int = None) -> List[Dict]:
        """Get subset of test data"""
        if self.test_data is None:
            self.load_test_data()
        n = n or self.config.num_test
        return self.test_data if n == 0 else self.test_data[:n]


class BedrockModelManager:
    """Manage Bedrock LLM client"""
    
    def __init__(self, config: Config):
        self.config = config
        self.client = None
    
    def get_client(self) -> BedrockClient:
        """Get or create Bedrock client"""
        if self.client is None:
            print(f"\n{'='*60}")
            print(f"Initializing Bedrock client...")
            print(f"Model: {self.config.model_id}")
            print(f"Region: {self.config.region_name}")
            print(f"{'='*60}")
            
            self.client = BedrockClient(
                model_id=self.config.model_id,
                region_name=self.config.region_name,
                bearer_token=self.config.bearer_token
            )
            
            print(f"✓ Bedrock client initialized")
        
        return self.client


class PromptBuilder:
    """Build prompts for syllogistic reasoning"""
    
    def __init__(self, prompts_dir: str = "prompts"):
        self.prompts_dir = prompts_dir
        self.system_prompt = self._load_prompt("pydatalog_detailed.txt")
    
    def _load_prompt(self, filename: str) -> str:
        """Load a prompt from file"""
        filepath = os.path.join(self.prompts_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Prompt file not found: {filepath}\n"
                f"Please ensure the prompts directory exists with all prompt files."
            )
    
    def use_simple_prompt(self):
        """Switch to using the simpler pyDatalog prompt"""
        self.system_prompt = self._load_prompt("pydatalog_simple.txt")
        return self
    
    def use_detailed_prompt(self):
        """Switch to using the detailed pyDatalog prompt (default)"""
        self.system_prompt = self._load_prompt("pydatalog_detailed.txt")
        return self
    
    def use_prolog_prompt(self):
        """Switch to using SWI-Prolog prompt"""
        self.system_prompt = self._load_prompt("prolog.txt")
        return self
    
    def use_cot_prompt(self):
        """Switch to using Chain-of-Thought prompt"""
        self.system_prompt = self._load_prompt("chain_of_thought.txt")
        return self


class BedrockInferenceEngine:
    """Run model inference using Bedrock"""
    
    def __init__(self, config: Config, model_manager: BedrockModelManager):
        self.config = config
        self.model_manager = model_manager
    
    def run_inference(
        self,
        data: List[Dict],
        prompt_builder: PromptBuilder
    ) -> List[Dict]:
        """Run inference on dataset using Bedrock"""
        results = []
        client = self.model_manager.get_client()
        
        print(f"\nRunning Bedrock inference on {len(data)} examples...")
        
        from tqdm import tqdm
        for item in tqdm(data, desc="Inference"):
            # Handle both 'text' and 'syllogism' keys
            syllogism_text = item.get('text') or item.get('syllogism', '')
            
            # Replace {syllogism} placeholder if present (for CoT prompt)
            user_prompt = syllogism_text
            
            try:
                # Call Bedrock
                response = client.generate(
                    prompt=user_prompt,
                    system_prompt=prompt_builder.system_prompt,
                    temperature=self.config.temperature,
                    top_k=self.config.top_k
                )
            except Exception as e:
                print(f"\nError generating response for {item['id']}: {e}")
                response = f"ERROR: {str(e)}"
            
            # Handle both 'label' and 'validity' keys
            label = item.get('label')
            if label is None and 'validity' in item:
                label = "VALID" if item['validity'] else "INVALID"
            
            results.append({
                'id': item['id'],
                'text': syllogism_text,
                'response': response,
                'label': label,
                'validity': item.get('validity'),  # Pass through for breakdown analysis
                'plausibility': item.get('plausibility')  # Pass through for breakdown analysis
            })
        
        print(f"✓ Inference complete")
        return results


# Import executor and evaluator classes (from repo root or lib fallback)
try:
    from semeval_pipeline_classes import (
        PrologExecutor,
        CotExecutor,
        Evaluator
    )
except ModuleNotFoundError:
    # When running from pamaldi_semeval_2026_11_task1, repo root is parent of that folder
    import sys
    from pathlib import Path
    _lib_dir = Path(__file__).resolve().parent
    _repo_root = _lib_dir.parent.parent  # semeval_2026_task_11 (where semeval_pipeline_classes.py lives)
    if str(_repo_root) not in sys.path:
        sys.path.insert(0, str(_repo_root))
    from semeval_pipeline_classes import (
        PrologExecutor,
        CotExecutor,
        Evaluator
    )

# Import official evaluation function
import sys
sys.path.insert(0, 'evaluation_kit/task 1 & 3')
try:
    from evaluation_script import run_full_scoring
    OFFICIAL_EVAL_AVAILABLE = True
except ImportError:
    OFFICIAL_EVAL_AVAILABLE = False
    print("Warning: Official evaluation script not found. Using internal evaluator.")


class SemEvalPipelineBedrock:
    """Main pipeline orchestrator for Bedrock"""
    
    def __init__(self, config: Config):
        self.config = config
        self.config.create_directories()
        
        self.data_loader = DataLoader(config)
        self.model_manager = BedrockModelManager(config)
        self.prompt_builder = PromptBuilder()
        self.inference_engine = BedrockInferenceEngine(config, self.model_manager)
        self.evaluator = Evaluator()
    
    def run_official_evaluation(
        self,
        ground_truth: List[Dict],
        predictions: List[Dict],
        executor
    ) -> Dict[str, float]:
        """
        Run official evaluation using the evaluation_script.py
        
        Args:
            ground_truth: List of ground truth items with 'id', 'validity', 'plausibility'
            predictions: List of predictions with 'id', 'prediction' ('VALID'/'INVALID'/'ERROR')
            executor: Executor instance with execution_dir attribute
        
        Returns:
            Dict with 'accuracy', 'content_effect', 'combined_score'
        """
        import json
        import os
        
        if not OFFICIAL_EVAL_AVAILABLE:
            print("Official evaluation script not available. Using internal evaluator.")
            return self.evaluator.evaluate_official(ground_truth, predictions)
        
        # Build reference file
        reference_data = []
        for item in ground_truth:
            reference_data.append({
                'id': item['id'],
                'validity': item.get('validity', item.get('label') == 'VALID'),
                'plausibility': item.get('plausibility')
            })
        
        # Build predictions file (convert to official format)
        predictions_official = []
        for pred in predictions:
            validity = pred['prediction'] == 'VALID'
            predictions_official.append({
                'id': pred['id'],
                'validity': validity
            })
        
        # Save files
        reference_file = os.path.join(executor.execution_dir, 'reference.json')
        predictions_file = os.path.join(executor.execution_dir, 'predictions.json')
        results_file = os.path.join(executor.execution_dir, 'evaluation_results.json')
        
        with open(reference_file, 'w') as f:
            json.dump(reference_data, f, indent=2)
        
        with open(predictions_file, 'w') as f:
            json.dump(predictions_official, f, indent=2)
        
        # Run official evaluation
        print("\n" + "="*80)
        print("RUNNING OFFICIAL EVALUATION")
        print("="*80)
        
        try:
            run_full_scoring(reference_file, predictions_file, results_file)
            
            # Load results
            with open(results_file, 'r') as f:
                eval_results = json.load(f)
            
            print("\n" + "="*80)
            print("OFFICIAL EVALUATION RESULTS")
            print("="*80)
            print(f"\nModel: {self.config.model_id}")
            print(f"Examples: {len(ground_truth)}")
            print(f"\nMetrics:")
            print(f"  Accuracy:        {eval_results['accuracy']:.2f}%")
            print(f"  Content Effect:  {eval_results['content_effect']:.2f}%")
            print(f"  Combined Score:  {eval_results['combined_score']:.2f}%")
            print("\n" + "="*80)
            
            return eval_results
            
        except Exception as e:
            print(f"\nError running official evaluation: {e}")
            print("Falling back to internal evaluator...")
            return self.evaluator.evaluate_official(ground_truth, predictions)
    
    def run_full_pipeline(self) -> Dict[str, Any]:
        """Run the complete pipeline"""
        print(f"\n{'#'*60}")
        print(f"# SemEval 2026 Task 11 - Bedrock Pipeline")
        print(f"# Model: {self.config.model_id}")
        print(f"{'#'*60}\n")
        
        print("Step 1: Loading data...")
        train_data = self.data_loader.get_train_subset()
        test_data = self.data_loader.get_test_subset()
        
        print("\nStep 2: Initializing Bedrock client...")
        client = self.model_manager.get_client()
        
        train_metrics = None
        executor = None
        
        if self.config.num_training > 0:
            print("\nStep 3: Running inference on training data...")
            train_results = self.inference_engine.run_inference(
                train_data, self.prompt_builder
            )
            
            print("\nStep 4: Executing training programs...")
            # Choose executor based on prompt type
            if "prolog" in self.prompt_builder.system_prompt.lower():
                executor = PrologExecutor(self.config, self.prompt_builder)
            elif "chain" in self.prompt_builder.system_prompt.lower():
                executor = CotExecutor(self.config, self.prompt_builder)
            else:
                executor = PrologExecutor(self.config, self.prompt_builder)
            
            train_predictions = executor.process_results(train_results)
            
            print("\nStep 5: Evaluating training results...")
            # Use official evaluation
            train_metrics = self.run_official_evaluation(
                train_data, 
                train_predictions,
                executor
            )
        
        if len(test_data) > 0:
            print("\nStep 6: Running inference on test data...")
            test_results = self.inference_engine.run_inference(
                test_data, self.prompt_builder
            )
            
            print("\nStep 7: Executing test programs...")
            if executor is None:
                # Create executor if not already created
                if "prolog" in self.prompt_builder.system_prompt.lower():
                    executor = PrologExecutor(self.config, self.prompt_builder)
                elif "chain" in self.prompt_builder.system_prompt.lower():
                    executor = CotExecutor(self.config, self.prompt_builder)
                else:
                    executor = PrologExecutor(self.config, self.prompt_builder)
            
            test_predictions = executor.process_results(test_results)
            
            output_file = os.path.join(
                self.config.results_dir,
                f"predictions_{self.config.model_id.replace('/', '_').replace('.', '_')}.json"
            )
            with open(output_file, 'w') as f:
                json.dump(test_predictions, f, indent=2)
            print(f"\n✓ Predictions saved to {output_file}")
        
        return {
            'train_metrics': train_metrics,
            'config': self.config.to_dict()
        }
