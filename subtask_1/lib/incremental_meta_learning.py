"""
Incremental Meta-Learning System

This module implements a feedback loop DURING training that improves the prompt
every N samples by analyzing accumulated errors.

Architecture:
- Every checkpoint_interval samples (default: 50):
  1. Read debug_failures.txt (current errors)
  2. Find NEW errors since last checkpoint
  3. Analyze errors with LLM
  4. Generate enhanced prompt building on previous learnings
  5. Continue training with improved prompt

The final enhanced prompt accumulates all learnings for the TEST phase.
"""

import os
import json
import re
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple


class IncrementalMetaLearning:
    """
    Manages incremental meta-learning checkpoints during training.
    
    Every checkpoint_interval samples:
    1. Analyze new errors
    2. Generate enhanced prompt
    3. Update pipeline to use new prompt
    """
    
    def __init__(
        self,
        output_dir: str,
        checkpoint_interval: int = 50,
        max_few_shots: int = 10,
        max_guidelines: int = 20,
        verbose: bool = True
    ):
        """
        Initialize incremental meta-learning.
        
        Args:
            output_dir: Directory for all outputs
            checkpoint_interval: Create checkpoint every N samples
            max_few_shots: Maximum few-shot examples to keep
            max_guidelines: Maximum guidelines to keep
            verbose: Print progress to console
        """
        self.output_dir = Path(output_dir)
        self.checkpoint_interval = checkpoint_interval
        self.max_few_shots = max_few_shots
        self.max_guidelines = max_guidelines
        self.verbose = verbose
        
        self.current_step = 0
        self.processed_samples = 0
        self.all_errors_seen = set()  # Track error IDs to find NEW errors
        
        # Create directories
        (self.output_dir / "logs").mkdir(parents=True, exist_ok=True)
        (self.output_dir / "checkpoints").mkdir(parents=True, exist_ok=True)
        (self.output_dir / "prompts").mkdir(parents=True, exist_ok=True)
        
        # Setup main logger
        self.main_logger = self._setup_logger(
            "MetaLearning_Main",
            self.output_dir / "logs" / "meta_learning_main.log"
        )
        
        # Initialize step 0 (base state)
        self._initialize_step_zero()
    
    def _setup_logger(self, name: str, log_file: Path) -> logging.Logger:
        """Setup a logger with file and console handlers."""
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)
        
        # Clear existing handlers
        logger.handlers = []
        
        # File handler - DEBUG level (everything)
        fh = logging.FileHandler(log_file, encoding='utf-8')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        logger.addHandler(fh)
        
        # Console handler - INFO level (summary only)
        if self.verbose:
            ch = logging.StreamHandler()
            ch.setLevel(logging.INFO)
            ch.setFormatter(logging.Formatter('%(message)s'))
            logger.addHandler(ch)
        
        return logger
    
    def _initialize_step_zero(self):
        """Initialize the base state (step 0)."""
        step_0 = {
            "step": 0,
            "timestamp": datetime.now().isoformat(),
            "samples_processed": 0,
            "total_errors": 0,
            "new_errors_this_step": 0,
            "cumulative_learnings": {
                "error_patterns": [],
                "few_shot_examples": [],
                "warning_signs": [],
                "guidelines": []
            },
            "prompt_version": "v0",
            "prompt_file": None
        }
        
        self._save_checkpoint(step_0)
        
        self.main_logger.info("=" * 80)
        self.main_logger.info("INCREMENTAL META-LEARNING INITIALIZED")
        self.main_logger.info("=" * 80)
        self.main_logger.info(f"Checkpoint interval: every {self.checkpoint_interval} samples")
        self.main_logger.info(f"Output directory: {self.output_dir}")
        self.main_logger.info(f"Max few-shots: {self.max_few_shots}")
        self.main_logger.info(f"Max guidelines: {self.max_guidelines}")
        self.main_logger.info("=" * 80)
    
    def _save_checkpoint(self, checkpoint_data: dict):
        """Save checkpoint to JSON file."""
        step = checkpoint_data["step"]
        filepath = self.output_dir / "checkpoints" / f"meta_learning_step_{step}.json"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)
        
        self.main_logger.debug(f"Checkpoint saved: {filepath}")
    
    def _load_checkpoint(self, step: int) -> Optional[dict]:
        """Load checkpoint from JSON file."""
        filepath = self.output_dir / "checkpoints" / f"meta_learning_step_{step}.json"
        
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def should_checkpoint(self, sample_index: int) -> bool:
        """Check if we should create a checkpoint at this sample."""
        return (sample_index + 1) % self.checkpoint_interval == 0
    
    def process_checkpoint(
        self,
        sample_index: int,
        debug_failures_path: str,
        llm_client,
        base_prompt: str
    ) -> str:
        """
        Process a checkpoint: analyze errors and generate enhanced prompt.
        
        Args:
            sample_index: Current sample index (0-based)
            debug_failures_path: Path to debug_failures.txt
            llm_client: LLM client for analysis
            base_prompt: Base extraction prompt
            
        Returns:
            Path to the new enhanced prompt
        """
        self.current_step += 1
        checkpoint_num = sample_index + 1
        
        # Setup checkpoint-specific logger
        checkpoint_logger = self._setup_logger(
            f"Checkpoint_{checkpoint_num}",
            self.output_dir / "logs" / f"checkpoint_{checkpoint_num:04d}.log"
        )
        
        checkpoint_logger.info("=" * 80)
        checkpoint_logger.info(f"CHECKPOINT {self.current_step} (after sample {checkpoint_num})")
        checkpoint_logger.info("=" * 80)
        checkpoint_logger.info(f"Timestamp: {datetime.now().isoformat()}")
        
        # Step 1: Read current errors from debug_failures.txt
        checkpoint_logger.info("\n--- STEP 1: Reading current errors ---")
        current_errors = self._read_debug_failures(debug_failures_path, checkpoint_logger)
        checkpoint_logger.info(f"Total errors in debug_failures.txt: {len(current_errors)}")
        
        # Step 2: Load previous checkpoint
        checkpoint_logger.info("\n--- STEP 2: Loading previous checkpoint ---")
        previous_checkpoint = self._load_checkpoint(self.current_step - 1)
        checkpoint_logger.info(f"Previous step: {previous_checkpoint['step']}")
        prev_few_shots = len(previous_checkpoint['cumulative_learnings']['few_shot_examples'])
        checkpoint_logger.info(f"Previous cumulative learnings: {prev_few_shots} few-shots")
        
        # Step 3: Find NEW errors (not seen before)
        checkpoint_logger.info("\n--- STEP 3: Identifying NEW errors ---")
        new_errors = self._find_new_errors(current_errors, checkpoint_logger)
        checkpoint_logger.info(f"New errors since last checkpoint: {len(new_errors)}")
        
        if new_errors:
            for i, err in enumerate(new_errors, 1):
                checkpoint_logger.debug(f"  New Error {i}:")
                checkpoint_logger.debug(f"    ID: {err.get('id', 'N/A')}")
                checkpoint_logger.debug(f"    Type: {err.get('type', 'N/A')}")
                syl_preview = err.get('syllogism', 'N/A')[:80]
                checkpoint_logger.debug(f"    Syllogism: {syl_preview}...")
        
        # Step 4: Analyze new errors with LLM
        checkpoint_logger.info("\n--- STEP 4: Analyzing new errors with LLM ---")
        if new_errors:
            new_learnings = self._analyze_errors(new_errors, llm_client, checkpoint_logger)
        else:
            checkpoint_logger.info("No new errors to analyze")
            new_learnings = {
                "error_patterns": [],
                "few_shot_examples": [],
                "warning_signs": [],
                "guidelines": []
            }
        
        # Step 5: Merge with previous learnings
        checkpoint_logger.info("\n--- STEP 5: Merging with previous learnings ---")
        cumulative_learnings = self._merge_learnings(
            previous_checkpoint["cumulative_learnings"],
            new_learnings,
            checkpoint_logger
        )
        
        # Step 6: Generate enhanced prompt
        checkpoint_logger.info("\n--- STEP 6: Generating enhanced prompt ---")
        enhanced_prompt = self._generate_enhanced_prompt(
            base_prompt,
            cumulative_learnings,
            checkpoint_logger
        )
        
        # Save enhanced prompt
        prompt_version = f"v{self.current_step}"
        prompt_file = self.output_dir / "prompts" / f"prompt_{prompt_version}.txt"
        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write(enhanced_prompt)
        checkpoint_logger.info(f"Enhanced prompt saved: {prompt_file}")
        
        # Step 7: Save checkpoint
        checkpoint_logger.info("\n--- STEP 7: Saving checkpoint ---")
        checkpoint_data = {
            "step": self.current_step,
            "timestamp": datetime.now().isoformat(),
            "samples_processed": checkpoint_num,
            "total_errors": len(current_errors),
            "new_errors_this_step": len(new_errors),
            "new_errors_details": [
                {
                    "id": e.get("id"),
                    "type": e.get("type"),
                    "syllogism_preview": e.get("syllogism", "")[:100]
                }
                for e in new_errors
            ],
            "cumulative_learnings": cumulative_learnings,
            "learnings_summary": {
                "total_patterns": len(cumulative_learnings["error_patterns"]),
                "total_few_shots": len(cumulative_learnings["few_shot_examples"]),
                "total_warnings": len(cumulative_learnings["warning_signs"]),
                "total_guidelines": len(cumulative_learnings["guidelines"])
            },
            "prompt_version": prompt_version,
            "prompt_file": str(prompt_file)
        }
        
        self._save_checkpoint(checkpoint_data)
        
        # Log to main logger
        self.main_logger.info(f"\n{'='*60}")
        self.main_logger.info(f"CHECKPOINT {self.current_step} COMPLETE (sample {checkpoint_num})")
        self.main_logger.info(f"{'='*60}")
        self.main_logger.info(f"  New errors analyzed: {len(new_errors)}")
        self.main_logger.info(f"  Cumulative few-shots: {len(cumulative_learnings['few_shot_examples'])}")
        self.main_logger.info(f"  Cumulative guidelines: {len(cumulative_learnings['guidelines'])}")
        self.main_logger.info(f"  New prompt: {prompt_file}")
        log_path = self.output_dir / 'logs' / f'checkpoint_{checkpoint_num:04d}.log'
        self.main_logger.info(f"  Detailed log: {log_path}")
        
        checkpoint_logger.info("\n" + "=" * 80)
        checkpoint_logger.info("CHECKPOINT COMPLETE")
        checkpoint_logger.info("=" * 80)
        
        return str(prompt_file)
    
    def _read_debug_failures(self, filepath: str, logger: logging.Logger) -> List[dict]:
        """Read and parse debug_failures.txt file."""
        logger.debug(f"Reading: {filepath}")
        
        errors = []
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse the debug failures format
            # Split by the separator line
            separator = "-" * 100
            error_blocks = content.split(separator)
            
            for block in error_blocks:
                if "[MISMATCH_FALSE_VALID]" in block or \
                   "[MISMATCH_FALSE_INVALID]" in block or \
                   "[EXTRACTION_ERROR]" in block:
                    error = self._parse_error_block(block, logger)
                    if error:
                        errors.append(error)
            
            logger.debug(f"Parsed {len(errors)} errors from file")
            
        except FileNotFoundError:
            logger.warning(f"File not found: {filepath}")
        except Exception as e:
            logger.error(f"Error reading file: {e}")
        
        return errors
    
    def _parse_error_block(self, block: str, logger: logging.Logger) -> Optional[dict]:
        """Parse a single error block from debug_failures.txt."""
        try:
            error = {}
            
            # Extract error type
            if "[MISMATCH_FALSE_VALID]" in block:
                error["type"] = "FALSE_VALID"
            elif "[MISMATCH_FALSE_INVALID]" in block:
                error["type"] = "FALSE_INVALID"
            elif "[EXTRACTION_ERROR]" in block:
                error["type"] = "EXTRACTION_ERROR"
            else:
                return None
            
            # Extract ID
            id_match = re.search(r'ID:\s*([a-f0-9-]+)', block)
            if id_match:
                error["id"] = id_match.group(1).strip()
            
            # Extract syllogism
            syl_match = re.search(r'### SILLOGISMO:\s*\n(.+?)(?=\n\n|\n###)', block, re.DOTALL)
            if syl_match:
                error["syllogism"] = syl_match.group(1).strip()
            
            # Extract ground truth validity
            if "Validity: VALID" in block:
                error["ground_truth"] = "VALID"
            elif "Validity: INVALID" in block:
                error["ground_truth"] = "INVALID"
            
            # Extract prediction
            pred_match = re.search(r'Prediction:\s*(VALID|INVALID)', block)
            if pred_match:
                error["prediction"] = pred_match.group(1)
            
            # Extract plausibility
            if "Plausibility: PLAUSIBLE" in block or "plausibility\": true" in block.lower():
                error["plausibility"] = "PLAUSIBLE"
            elif "Plausibility: IMPLAUSIBLE" in block or "plausibility\": false" in block.lower():
                error["plausibility"] = "IMPLAUSIBLE"
            
            # Extract form if present
            form_match = re.search(r'Form:\s*([A-Z]{3}-\d)', block)
            if form_match:
                error["extracted_form"] = form_match.group(1)
            
            return error if error.get("id") else None
            
        except Exception as e:
            logger.debug(f"Error parsing block: {e}")
            return None
    
    def _find_new_errors(self, current_errors: List[dict], logger: logging.Logger) -> List[dict]:
        """Find errors that haven't been seen in previous checkpoints."""
        new_errors = []
        
        for error in current_errors:
            error_id = error.get("id")
            if error_id and error_id not in self.all_errors_seen:
                new_errors.append(error)
                self.all_errors_seen.add(error_id)
                logger.debug(f"New error found: {error_id}")
        
        return new_errors
    
    def _analyze_errors(
        self,
        errors: List[dict],
        llm_client,
        logger: logging.Logger
    ) -> dict:
        """Analyze errors using LLM to generate learnings."""
        logger.info(f"Analyzing {len(errors)} errors with LLM...")
        
        # Format errors for LLM
        error_text = ""
        for i, err in enumerate(errors, 1):
            error_text += f"""
### Error {i}: {err.get('type', 'UNKNOWN')}
- ID: {err.get('id', 'N/A')}
- Syllogism: {err.get('syllogism', 'N/A')}
- Ground Truth: {err.get('ground_truth', 'N/A')}
- Prediction: {err.get('prediction', 'N/A')}
- Extracted Form: {err.get('extracted_form', 'N/A')}
- Plausibility: {err.get('plausibility', 'N/A')}
"""
        
        # Analysis prompt (no JSON curly braces to avoid .format() issues)
        analysis_prompt = f"""You are an expert in formal logic and syllogistic reasoning.

Analyze these errors from a syllogism validity prediction system:

{error_text}

For each error, determine:
1. What went wrong (root cause)
2. How to prevent this error
3. A corrected example that could be used as a few-shot

Return your analysis as valid JSON with this structure:
- "error_patterns": array of objects with pattern_name, description, affected_error_ids, prevention
- "few_shot_examples": array of objects with syllogism, correct_analysis, correct_validity, common_mistake
- "warning_signs": array of objects with pattern, risk, action
- "guidelines": array of strings with specific guidelines

Focus on actionable insights that will prevent similar errors.
Return ONLY valid JSON, no other text."""

        logger.debug("Sending analysis request to LLM...")
        logger.debug(f"Prompt length: {len(analysis_prompt)} chars")
        
        try:
            response = llm_client.generate(
                prompt=analysis_prompt,
                temperature=0.0,
                max_tokens=3000
            )
            
            logger.debug(f"LLM response length: {len(response)} chars")
            
            # Parse JSON from response
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                learnings = json.loads(json_match.group(1))
            else:
                # Try to find JSON object directly
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                if json_start != -1 and json_end > json_start:
                    learnings = json.loads(response[json_start:json_end])
                else:
                    raise ValueError("No JSON found in response")
            
            # Ensure all keys exist
            learnings.setdefault("error_patterns", [])
            learnings.setdefault("few_shot_examples", [])
            learnings.setdefault("warning_signs", [])
            learnings.setdefault("guidelines", [])
            
            logger.info(f"Analysis complete:")
            logger.info(f"  - Patterns found: {len(learnings.get('error_patterns', []))}")
            logger.info(f"  - Few-shots generated: {len(learnings.get('few_shot_examples', []))}")
            logger.info(f"  - Warnings identified: {len(learnings.get('warning_signs', []))}")
            logger.info(f"  - Guidelines added: {len(learnings.get('guidelines', []))}")
            
            return learnings
            
        except Exception as e:
            logger.error(f"Error analyzing with LLM: {e}")
            return {
                "error_patterns": [],
                "few_shot_examples": [],
                "warning_signs": [],
                "guidelines": []
            }
    
    def _merge_learnings(
        self,
        previous: dict,
        new: dict,
        logger: logging.Logger
    ) -> dict:
        """Merge new learnings with previous cumulative learnings."""
        merged = {
            "error_patterns": previous.get("error_patterns", []) + new.get("error_patterns", []),
            "few_shot_examples": previous.get("few_shot_examples", []) + new.get("few_shot_examples", []),
            "warning_signs": previous.get("warning_signs", []) + new.get("warning_signs", []),
            "guidelines": previous.get("guidelines", []) + new.get("guidelines", [])
        }
        
        # Deduplicate guidelines
        merged["guidelines"] = list(dict.fromkeys(merged["guidelines"]))
        
        # Limit few-shots to most recent N (to avoid prompt bloat)
        if len(merged["few_shot_examples"]) > self.max_few_shots:
            logger.info(f"Limiting few-shots from {len(merged['few_shot_examples'])} to {self.max_few_shots}")
            merged["few_shot_examples"] = merged["few_shot_examples"][-self.max_few_shots:]
        
        # Limit guidelines
        if len(merged["guidelines"]) > self.max_guidelines:
            logger.info(f"Limiting guidelines from {len(merged['guidelines'])} to {self.max_guidelines}")
            merged["guidelines"] = merged["guidelines"][-self.max_guidelines:]
        
        logger.info(f"Merged learnings:")
        logger.info(f"  - Total patterns: {len(merged['error_patterns'])}")
        logger.info(f"  - Total few-shots: {len(merged['few_shot_examples'])}")
        logger.info(f"  - Total warnings: {len(merged['warning_signs'])}")
        logger.info(f"  - Total guidelines: {len(merged['guidelines'])}")
        
        return merged
    
    def _generate_enhanced_prompt(
        self,
        base_prompt: str,
        learnings: dict,
        logger: logging.Logger
    ) -> str:
        """Generate enhanced prompt by adding learnings to base prompt."""
        logger.info("Generating enhanced prompt...")
        
        enhanced = base_prompt
        
        # Add few-shot examples section
        if learnings.get("few_shot_examples"):
            few_shots_section = "\n\n## ⚠️ ERROR-DERIVED EXAMPLES (Study These Carefully!)\n\n"
            few_shots_section += "These examples come from actual errors. Pay special attention:\n\n"
            
            for i, ex in enumerate(learnings["few_shot_examples"], 1):
                few_shots_section += f"### Tricky Case {i}\n\n"
                few_shots_section += f"**Syllogism:** \"{ex.get('syllogism', 'N/A')}\"\n\n"
                few_shots_section += f"**Common Mistake:** {ex.get('common_mistake', 'N/A')}\n\n"
                few_shots_section += f"**Correct Analysis:** {ex.get('correct_analysis', 'N/A')}\n\n"
                few_shots_section += f"**Correct Answer:** {ex.get('correct_validity', 'N/A')}\n\n"
                few_shots_section += "---\n\n"
            
            # Insert before existing examples
            insert_pos = enhanced.find("## WORKED EXAMPLE")
            if insert_pos != -1:
                enhanced = enhanced[:insert_pos] + few_shots_section + enhanced[insert_pos:]
            else:
                enhanced += few_shots_section
        
        # Add warning signs section
        if learnings.get("warning_signs"):
            warnings_section = "\n\n## 🚨 WARNING SIGNS\n\n"
            warnings_section += "When you encounter these patterns, be extra careful:\n\n"
            
            for w in learnings["warning_signs"]:
                warnings_section += f"- **{w.get('pattern', 'N/A')}**\n"
                warnings_section += f"  - Risk: {w.get('risk', 'N/A')}\n"
                warnings_section += f"  - Action: {w.get('action', 'N/A')}\n\n"
            
            # Insert before "Important Reminders" or at end
            insert_pos = enhanced.find("## Important")
            if insert_pos != -1:
                enhanced = enhanced[:insert_pos] + warnings_section + enhanced[insert_pos:]
            else:
                enhanced += warnings_section
        
        # Add guidelines section
        if learnings.get("guidelines"):
            guidelines_section = "\n\n## 📋 LEARNED GUIDELINES\n\n"
            for i, g in enumerate(learnings["guidelines"], 1):
                guidelines_section += f"{i}. {g}\n"
            guidelines_section += "\n"
            
            # Insert before final instruction
            insert_pos = enhanced.find("Now extract the structure")
            if insert_pos != -1:
                enhanced = enhanced[:insert_pos] + guidelines_section + enhanced[insert_pos:]
            else:
                enhanced += guidelines_section
        
        logger.info(f"Prompt enhanced:")
        logger.info(f"  - Original length: {len(base_prompt)} chars")
        logger.info(f"  - Enhanced length: {len(enhanced)} chars")
        logger.info(f"  - Added: {len(enhanced) - len(base_prompt)} chars")
        
        return enhanced
    
    def finalize(self) -> Optional[str]:
        """
        Finalize meta-learning and return path to final prompt.
        Called at the end of training phase.
        """
        self.main_logger.info("\n" + "=" * 80)
        self.main_logger.info("FINALIZING META-LEARNING")
        self.main_logger.info("=" * 80)
        
        # Load latest checkpoint
        latest_checkpoint = self._load_checkpoint(self.current_step)
        
        if latest_checkpoint and latest_checkpoint.get("prompt_file"):
            # Copy latest prompt as final
            latest_prompt = Path(latest_checkpoint["prompt_file"])
            final_prompt_path = self.output_dir / "prompts" / "prompt_final.txt"
            
            if latest_prompt.exists():
                shutil.copy(latest_prompt, final_prompt_path)
                self.main_logger.info(f"Final prompt: {final_prompt_path}")
            
            # Log summary
            learnings = latest_checkpoint.get("cumulative_learnings", {})
            self.main_logger.info(f"\nMETA-LEARNING SUMMARY:")
            self.main_logger.info(f"  - Total checkpoints: {self.current_step}")
            self.main_logger.info(f"  - Total samples processed: {latest_checkpoint.get('samples_processed', 0)}")
            self.main_logger.info(f"  - Total errors seen: {len(self.all_errors_seen)}")
            self.main_logger.info(f"  - Final few-shots: {len(learnings.get('few_shot_examples', []))}")
            self.main_logger.info(f"  - Final guidelines: {len(learnings.get('guidelines', []))}")
            
            return str(final_prompt_path)
        
        self.main_logger.info("No checkpoints created - using base prompt")
        return None
    
    def get_current_prompt_path(self) -> Optional[str]:
        """Get path to current enhanced prompt (or None if at step 0)."""
        if self.current_step == 0:
            return None
        
        checkpoint = self._load_checkpoint(self.current_step)
        if checkpoint:
            return checkpoint.get("prompt_file")
        return None
    
    def get_summary(self) -> dict:
        """Get summary of meta-learning progress."""
        latest = self._load_checkpoint(self.current_step)
        
        return {
            "current_step": self.current_step,
            "total_errors_seen": len(self.all_errors_seen),
            "checkpoint_interval": self.checkpoint_interval,
            "latest_checkpoint": latest,
            "output_dir": str(self.output_dir)
        }
