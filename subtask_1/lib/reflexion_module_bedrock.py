"""
Reflexion Module for Bedrock - Self-Correcting Executor Wrapper
Adapted to work with AWS Bedrock instead of HuggingFace models

TRUE REFLEXION IMPLEMENTATION:
- Label-free reflection generation (works for both training and test)
- Persistent memory across attempts
- LLM-generated insights, not just error feedback
- Configurable modes for different use cases
"""

import os
import json
import time
import threading
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Tuple
from tqdm import tqdm


class FailureType(Enum):
    """Classification of failure types"""
    SYNTAX_ERROR = "syntax_error"
    RUNTIME_ERROR = "runtime_error"
    WRONG_PREDICTION = "wrong_prediction"
    NO_CODE_EXTRACTED = "no_code_extracted"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


class ReflexionMode(Enum):
    """Controls how reflexion uses ground truth labels"""
    LABEL_FREE = "label_free"           # No label hints - works for test data
    LABEL_GUIDED = "label_guided"       # Uses labels for hints - training analysis only
    EXECUTION_ONLY = "execution_only"   # Only retry on execution errors (syntax, runtime, timeout)


@dataclass
class ReflexionAttempt:
    """Record of a single attempt"""
    attempt_number: int
    code: Optional[str]
    prediction: str
    stdout: str
    stderr: str
    failure_type: FailureType
    reflection_prompt: Optional[str]
    generated_reflection: Optional[str]
    timestamp: str
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        d = asdict(self)
        d['failure_type'] = self.failure_type.value
        return d


@dataclass
class ReflexionResult:
    """Complete result for one syllogism"""
    syllogism_id: str
    syllogism_text: str
    ground_truth: Optional[str]
    final_prediction: str
    success: Optional[bool]  # None if ground truth unavailable
    total_attempts: int
    attempts: List[ReflexionAttempt]
    first_attempt_success: Optional[bool]  # None if ground truth unavailable
    reflections_memory: List[str]
    validity: Optional[bool] = None
    plausibility: Optional[bool] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'syllogism_id': self.syllogism_id,
            'syllogism_text': self.syllogism_text,
            'ground_truth': self.ground_truth,
            'final_prediction': self.final_prediction,
            'success': self.success,
            'total_attempts': self.total_attempts,
            'attempts': [a.to_dict() for a in self.attempts],
            'first_attempt_success': self.first_attempt_success,
            'reflections_memory': self.reflections_memory,
            'validity': self.validity,
            'plausibility': self.plausibility
        }


class ReflexionExecutorBedrock:
    """Self-correcting executor with reflexion loop for Bedrock"""
    
    def __init__(
        self,
        config,
        model_manager,
        prompt_builder,
        inference_engine,
        base_executor,
        max_attempts: int = 3,
        use_ground_truth: bool = True,
        reflexion_mode: ReflexionMode = ReflexionMode.LABEL_FREE,
        verbose: bool = False,
        run_name: str = None,  # Custom name for the run (e.g., "train", "test")
        learned_patterns_file: str = None  # Path to learned_patterns.txt from training
    ):
        self.config = config
        self.model_manager = model_manager
        self.prompt_builder = prompt_builder
        self.inference_engine = inference_engine
        self.base_executor = base_executor
        self.max_attempts = max_attempts
        self.use_ground_truth = use_ground_truth
        self.reflexion_mode = reflexion_mode
        self.verbose = verbose
        self.run_name = run_name
        self.learned_patterns_file = learned_patterns_file
        
        # Augment prompt with learned patterns if provided
        if learned_patterns_file:
            self._augment_prompt_with_patterns(learned_patterns_file)
        
        # Get Bedrock client
        self.client = model_manager.get_client()
        
        # Create timestamped execution folder with optional run_name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if run_name:
            folder_name = f"reflexion_{run_name}_{timestamp}"
        else:
            folder_name = f"reflexion_{timestamp}"
        
        self.execution_dir = os.path.join(
            config.results_dir,
            folder_name
        )
        # Results and logs in the same directory
        self.programs_dir = self.execution_dir
        self.logs_dir = self.execution_dir
        
        os.makedirs(self.execution_dir, exist_ok=True)
        
        # Load reflexion prompts from files
        self.prompts_dir = "prompts"
        self._load_prompts()
        
        # Save configuration
        self._save_config()
        
        print(f"✓ ReflexionExecutor (Bedrock) initialized")
        print(f"  Max attempts: {max_attempts}")
        print(f"  Use ground truth: {use_ground_truth}")
        print(f"  Reflexion mode: {reflexion_mode.value}")  # NEW
        print(f"  Execution folder: {self.execution_dir}")
    
    def _load_prompts(self):
        """Load all reflexion prompts from text files"""
        prompt_files = {
            'base': 'reflexion_base.txt',
            'syntax_error': 'reflexion_syntax_error.txt',
            'runtime_error': 'reflexion_runtime_error.txt',
            'wrong_prediction': 'reflexion_wrong_prediction.txt',
            'no_code': 'reflexion_no_code.txt',
            'timeout': 'reflexion_timeout.txt',
            'unknown': 'reflexion_unknown.txt',
            'attempt_history': 'reflexion_attempt_history.txt',
            'generate_reflection': 'reflexion_generate_reflection.txt',
            'with_memory': 'reflexion_with_memory.txt'
        }
        
        self.reflexion_prompts = {}
        
        for key, filename in prompt_files.items():
            filepath = os.path.join(self.prompts_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    self.reflexion_prompts[key] = f.read()
            except FileNotFoundError:
                print(f"⚠ Warning: Prompt file not found: {filepath}")
                self.reflexion_prompts[key] = f"[{key} prompt not found]"
        
        print(f"  Loaded {len(self.reflexion_prompts)} reflexion prompts")
    
    def _augment_prompt_with_patterns(self, patterns_file: str):
        """
        Augment the system prompt with learned patterns from training.
        This helps the model avoid mistakes identified during training.
        """
        if not os.path.exists(patterns_file):
            print(f"⚠ Warning: Learned patterns file not found: {patterns_file}")
            return
        
        try:
            with open(patterns_file, 'r', encoding='utf-8') as f:
                patterns_content = f.read()
            
            # Extract just the patterns (skip the header)
            if "=" * 80 in patterns_content:
                # Find the actual content after headers
                parts = patterns_content.split("=" * 80)
                if len(parts) >= 3:
                    patterns_content = parts[-1].strip()
            
            # Augment the prompt builder's system prompt
            augmentation = f"""

---

## LEARNED PATTERNS FROM TRAINING (IMPORTANT - AVOID THESE MISTAKES)

The following patterns were identified from training failures. Pay special attention to avoid these errors:

{patterns_content}

---

"""
            # Append to the existing system prompt
            self.prompt_builder.system_prompt = self.prompt_builder.system_prompt + augmentation
            
            print(f"✓ Prompt augmented with learned patterns from: {patterns_file}")
            
        except Exception as e:
            print(f"⚠ Warning: Failed to load patterns file: {e}")
    
    def _save_config(self):
        """Save run configuration"""
        config_data = {
            'model_id': self.config.model_id,
            'max_attempts': self.max_attempts,
            'use_ground_truth': self.use_ground_truth,
            'reflexion_mode': self.reflexion_mode.value,
            'temperature': self.config.temperature,
            'top_k': self.config.top_k,
            'timestamp': datetime.now().isoformat(),
            'prompt_type': 'prolog' if 'prolog' in self.prompt_builder.system_prompt.lower() else 'other',
            'learned_patterns_file': self.learned_patterns_file
        }
        
        config_file = os.path.join(self.execution_dir, 'config.json')
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
    
    def _classify_failure(
        self,
        code: Optional[str],
        prediction: str,
        stderr: str,
        ground_truth: Optional[str]
    ) -> FailureType:
        """Classify the type of failure"""
        if code is None:
            return FailureType.NO_CODE_EXTRACTED
        
        if prediction == "TIMEOUT":
            return FailureType.TIMEOUT
        
        if prediction == "ERROR":
            if "SyntaxError" in stderr or "IndentationError" in stderr:
                return FailureType.SYNTAX_ERROR
            else:
                return FailureType.RUNTIME_ERROR
        
        # Only classify as wrong_prediction if we have ground truth
        if ground_truth and prediction != ground_truth:
            return FailureType.WRONG_PREDICTION
        
        return FailureType.UNKNOWN
    
    def _is_execution_error(self, failure_type: FailureType) -> bool:
        """Check if failure is an execution error (fixable without labels)"""
        return failure_type in [
            FailureType.SYNTAX_ERROR,
            FailureType.RUNTIME_ERROR,
            FailureType.NO_CODE_EXTRACTED,
            FailureType.TIMEOUT
        ]
    
    def _generate_reflection(
        self,
        syllogism: str,
        code: str,
        failure_type: FailureType,
        stderr: str,
        attempt_number: int,
        prediction: str = None,
        ground_truth: str = None
    ) -> str:
        """
        Generate reflection using LLM - LABEL-FREE by default.
        
        The reflection focuses on self-analysis and logical reasoning,
        NOT on hints about what the correct answer should be.
        
        This allows Reflexion to work on test data without labels.
        """
        
        # Determine if we should use label hints
        use_label_hints = (
            self.reflexion_mode == ReflexionMode.LABEL_GUIDED 
            and ground_truth is not None
        )
        
        # Build error section
        if stderr and stderr.strip() and stderr != "No error message":
            error_section = f"Error: {stderr}"
        elif failure_type == FailureType.WRONG_PREDICTION:
            if use_label_hints:
                error_section = "Your code ran but produced an INCORRECT validity result."
            else:
                error_section = "Your code ran. Verify the result is logically correct."
        else:
            error_section = f"Error: {stderr if stderr else 'No error message'}"
        
        # Build reflection focus based on failure type
        if failure_type == FailureType.SYNTAX_ERROR:
            reflection_focus = """1. What exact syntax mistake did you make? (missing period, wrong operator, etc.)
2. What is the corrected syntax for that specific line/rule?"""
        
        elif failure_type == FailureType.RUNTIME_ERROR:
            reflection_focus = """1. What undefined predicate or logical error caused the runtime failure?
2. What fact or rule definition must you add to fix this?"""
        
        elif failure_type == FailureType.WRONG_PREDICTION:
            if use_label_hints and prediction and ground_truth:
                # LABEL-GUIDED mode: provide directional hints
                if prediction == "VALID" and ground_truth == "INVALID":
                    reflection_focus = """⚠️ Your prediction (VALID) is INCORRECT. The syllogism is actually INVALID.

1. What logical fallacy does this syllogism commit? (undistributed middle, illicit major/minor, etc.)
2. Describe a specific COUNTEREXAMPLE: what entities would make premises true but conclusion FALSE?

Hint: For "All A are B. All C are B. ∴ Some C are not A" (undistributed middle)
→ Counterexample: Make the C entity ALSO be an A, so no C exists that isn't A."""
                
                elif prediction == "INVALID" and ground_truth == "VALID":
                    reflection_focus = """⚠️ Your prediction (INVALID) is INCORRECT. The syllogism is actually VALID.

1. What encoding mistake prevented the conclusion from succeeding? (wrong rule direction, missing witness fact, wrong conclusion check type)
2. Trace the inference: does your witness connect through premises to satisfy the conclusion?"""
                
                else:
                    reflection_focus = """1. What caused the wrong prediction?
2. What specific change will produce the correct validity result?"""
            else:
                # LABEL-FREE mode: guide self-analysis without revealing answer
                reflection_focus = """STEP 1: Re-analyze the syllogism structure
- Identify each premise type (A: All S are P, E: No S is P, I: Some S are P, O: Some S are not P)
- Identify the conclusion type
- Check: Is the middle term distributed in at least one premise?

STEP 2: Check for logical fallacies
- Undistributed middle: "All A are B. All C are B." does NOT imply any A-C relationship
- Illicit major/minor: Is a term distributed in conclusion but not in premises?
- Two negative premises: Cannot yield a valid conclusion
- Negative premise with affirmative conclusion: Invalid

STEP 3: Verify your code strategy
- If syllogism appears VALID: Did you build a proper witness? Check rule directions.
- If syllogism appears INVALID: Did you build a proper COUNTEREXAMPLE where premises hold but conclusion fails?

STEP 4: Answer these questions
1. Re-read the syllogism. What is your assessment: VALID or INVALID? Why?
2. Does your Prolog code implement the correct strategy for that assessment?
3. What specific change will align your code with your logical analysis?"""
        
        elif failure_type == FailureType.NO_CODE_EXTRACTED:
            reflection_focus = """1. What formatting issue prevented code extraction?
2. Output ONLY executable Prolog code in ```prolog blocks."""
        
        elif failure_type == FailureType.TIMEOUT:
            reflection_focus = """1. What caused the infinite loop? (circular rules, unbounded recursion)
2. How will you restructure to avoid non-termination?"""
        
        else:  # UNKNOWN
            reflection_focus = """1. What unexpected behavior occurred?
2. What is your hypothesis for the cause and how will you fix it?"""
        
        # Assemble the full reflection request
        reflection_request = f"""You attempted to solve this syllogism:

{syllogism}

Your code (Attempt {attempt_number}):
```
{code if code else "No code generated"}
```

Result: {failure_type.value}
{error_section}

================================================================================
SELF-ANALYSIS TASK
================================================================================

{reflection_focus}

RULES:
- REASON from the syllogism structure, not from trial-and-error
- Be SPECIFIC: name exact predicates, facts, or rules that need changing
- Be CONCRETE: reference the actual premise/conclusion types (A/E/I/O)
- Focus on WHY your approach may be wrong, not just WHAT to change

Your analysis and reflection:"""
        
        result = [None]
        exception = [None]
        
        def call_bedrock_reflection():
            try:
                result[0] = self.client.generate(
                    prompt=reflection_request,
                    system_prompt="You are a logician analyzing a failed syllogism solution. Focus on logical reasoning and structural analysis. Do not guess - reason carefully about validity.",
                    temperature=0.3,
                    top_k=self.config.top_k
                )
            except Exception as e:
                exception[0] = e
        
        try:
            if self.verbose:
                print(f"    [Bedrock] Connecting to generate reflection...", end=" ")
            
            # Run in thread with timeout
            thread = threading.Thread(target=call_bedrock_reflection)
            thread.daemon = True
            thread.start()
            thread.join(timeout=60)  # 60 second timeout for reflection generation
            
            if thread.is_alive():
                if self.verbose:
                    print(f"✗ TIMEOUT (60s)")
                return f"Attempt {attempt_number} failed with {failure_type.value} (reflection generation timed out)"
            elif exception[0]:
                if self.verbose:
                    print(f"✗ FAILED: {exception[0]}")
                return f"Attempt {attempt_number} failed with {failure_type.value}"
            else:
                reflection = result[0]
                if self.verbose:
                    print(f"✓ OK ({len(reflection)} chars)")
                
                # Truncate if too long
                if len(reflection) > 600:
                    reflection = reflection[:600] + "..."
                
                return reflection.strip()
            
        except Exception as e:
            if self.verbose:
                print(f"✗ FAILED: {e}")
            else:
                print(f"Warning: Failed to generate reflection: {e}")
            return f"Attempt {attempt_number} failed with {failure_type.value}"
    
    def _build_reflection_prompt_with_memory(
        self,
        syllogism: str,
        code: str,
        failure_type: FailureType,
        stderr: str,
        reflections_memory: List[str]
    ) -> str:
        """
        Build prompt that includes ALL past reflections from memory.
        
        This is the core of True Reflexion - accumulated insights
        from previous attempts guide future attempts.
        """
        # Format memory section
        memory_section = ""
        if reflections_memory:
            memory_section = "=" * 60 + "\n"
            memory_section += "LESSONS FROM PREVIOUS ATTEMPTS (apply these insights):\n"
            memory_section += "=" * 60 + "\n"
            for reflection in reflections_memory:
                memory_section += f"• {reflection}\n"
            memory_section += "\n"
        
        # Get failure-specific guidance from loaded prompts
        failure_guidance_map = {
            FailureType.SYNTAX_ERROR: self.reflexion_prompts['syntax_error'],
            FailureType.RUNTIME_ERROR: self.reflexion_prompts['runtime_error'],
            FailureType.WRONG_PREDICTION: self.reflexion_prompts['wrong_prediction'],
            FailureType.NO_CODE_EXTRACTED: self.reflexion_prompts['no_code'],
            FailureType.TIMEOUT: self.reflexion_prompts['timeout'],
            FailureType.UNKNOWN: self.reflexion_prompts['unknown']
        }
        
        failure_guidance = failure_guidance_map.get(
            failure_type,
            self.reflexion_prompts['unknown']
        )
        
        # Build complete prompt using template
        template = self.reflexion_prompts.get('with_memory', '')
        
        if template and '{memory_section}' in template:
            prompt = template.format(
                memory_section=memory_section,
                syllogism=syllogism,
                failure_type=failure_type.value,
                stderr=stderr if stderr else "No error message",
                code=code,
                failure_guidance=failure_guidance
            )
        else:
            # Fallback if template not available
            prompt = f"""{memory_section}
CURRENT TASK
============
Solve this syllogism by generating Prolog code:

{syllogism}

PREVIOUS ATTEMPT FAILED
=======================
Failure type: {failure_type.value}
Error message: {stderr if stderr else "No error message"}

Previous code:
```
{code}
```

{failure_guidance}

INSTRUCTIONS
============
1. Review the lessons learned above (if any)
2. Analyze what went wrong in the previous attempt
3. Generate CORRECTED Prolog code that addresses all identified issues
4. Ensure the code handles the syllogism structure correctly

Generate your corrected solution:"""
        
        return prompt
    
    def _generate_with_reflection(
        self,
        reflection_prompt: str
    ) -> str:
        """Generate new code using Bedrock with reflection feedback"""
        result = [None]
        exception = [None]
        
        def call_bedrock():
            try:
                result[0] = self.client.generate(
                    prompt=reflection_prompt,
                    system_prompt=self.prompt_builder.system_prompt,
                    temperature=self.config.temperature,
                    top_k=self.config.top_k
                )
            except Exception as e:
                exception[0] = e
        
        if self.verbose:
            print(f"    [Bedrock] Connecting to generate new code...", end=" ")
        
        # Run in thread with timeout
        thread = threading.Thread(target=call_bedrock)
        thread.daemon = True
        thread.start()
        thread.join(timeout=90)  # 90 second timeout for Bedrock calls
        
        if thread.is_alive():
            if self.verbose:
                print(f"✗ TIMEOUT (90s)")
            return "ERROR: Bedrock call timed out after 90 seconds"
        elif exception[0]:
            if self.verbose:
                print(f"✗ FAILED: {exception[0]}")
            return f"ERROR: {str(exception[0])}"
        else:
            if self.verbose:
                print(f"✓ OK ({len(result[0])} chars)")
            return result[0]
    
    def _attempt_execution(
        self,
        syllogism_id: str,
        syllogism_text: str,
        response: str,
        attempt_number: int
    ) -> Tuple[Optional[str], str, str, str]:
        """Attempt to execute code from response with timeout protection"""
        if self.verbose:
            print(f"extracting code...", end=" ")
        
        # Extract code
        code = self.base_executor.extract_code(response)
        
        if code:
            if self.verbose:
                print(f"✓ ({len(code)} chars) executing...", end=" ")
            
            # Save program
            program_file = f"{syllogism_id}_attempt_{attempt_number}.py"
            filepath = os.path.join(self.programs_dir, program_file)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(code)
            
            # Execute with timeout using threading
            result = [None, None, None]  # prediction, stdout, stderr
            exception = [None]
            
            def execute_with_timeout():
                try:
                    result[0], result[1], result[2] = self.base_executor.execute_program(filepath)
                except Exception as e:
                    exception[0] = e
            
            # Run in thread with timeout
            thread = threading.Thread(target=execute_with_timeout)
            thread.daemon = True
            thread.start()
            thread.join(timeout=30)  # 30 second timeout
            
            if thread.is_alive():
                # Timeout occurred
                if self.verbose:
                    print(f"⚠ TIMEOUT (30s)")
                prediction = "TIMEOUT"
                stdout = ""
                stderr = "Execution timed out after 30 seconds (possible infinite loop)"
            elif exception[0]:
                if self.verbose:
                    print(f"✗ ERROR: {exception[0]}")
                prediction = "ERROR"
                stdout = ""
                stderr = str(exception[0])
            else:
                prediction, stdout, stderr = result
                if self.verbose:
                    print(f"done", end=" ")
        else:
            if self.verbose:
                print(f"✗ no code found", end=" ")
            prediction = "ERROR"
            stdout = ""
            stderr = "No code extracted from response"
        
        return code, prediction, stdout, stderr
    
    def _should_retry(
        self,
        failure_type: FailureType,
        prediction: str,
        ground_truth: Optional[str],
        attempt_num: int
    ) -> bool:
        """
        Determine if we should retry based on mode and failure type.
        
        This is critical for test-time behavior where we don't have labels.
        """
        # Never retry if max attempts reached
        if attempt_num >= self.max_attempts:
            return False
        
        # EXECUTION_ONLY mode: only retry on execution errors
        if self.reflexion_mode == ReflexionMode.EXECUTION_ONLY:
            return self._is_execution_error(failure_type)
        
        # If we have ground truth and prediction is correct, don't retry
        if ground_truth and prediction == ground_truth:
            return False
        
        # If we have ground truth, retry on any failure
        if ground_truth:
            return True
        
        # NO GROUND TRUTH (test data):
        # Only retry on execution errors, not "wrong prediction" (we can't know!)
        if self._is_execution_error(failure_type):
            return True
        
        # Got a prediction (VALID/INVALID) but no way to verify - stop here
        if prediction in ["VALID", "INVALID"]:
            return False
        
        # Unknown state - try to recover
        return True
    
    def _process_single_syllogism(
        self,
        item: Dict,
        initial_response: str
    ) -> ReflexionResult:
        """Process a single syllogism with TRUE reflexion loop"""
        syllogism_id = item['id']
        syllogism_text = item['text']
        ground_truth = item.get('label')  # May be None for test data
        
        # Capture validity and plausibility from original data
        validity = item.get('validity')
        plausibility = item.get('plausibility')
        
        # Verbose logging
        if self.verbose:
            print(f"\n{'─'*60}")
            print(f"Processing: {syllogism_id[:20]}...")
            print(f"Ground truth: {ground_truth or 'N/A'}")
        
        attempts = []
        current_response = initial_response
        reflections_memory = []  # Persistent memory for this syllogism
        success = None  # Will be determined if we have ground truth
        
        for attempt_num in range(1, self.max_attempts + 1):
            if self.verbose:
                print(f"  Attempt {attempt_num}/{self.max_attempts}...", end=" ")
            
            # Attempt execution
            code, prediction, stdout, stderr = self._attempt_execution(
                syllogism_id,
                syllogism_text,
                current_response,
                attempt_num
            )
            
            # Classify failure
            failure_type = self._classify_failure(code, prediction, stderr, ground_truth)
            
            if self.verbose:
                status_icon = "✓" if prediction in ["VALID", "INVALID"] else "✗"
                print(f"{status_icon} Prediction: {prediction} | Type: {failure_type.value}")
                if stderr and failure_type != FailureType.UNKNOWN:
                    print(f"    Error: {stderr[:80]}..." if len(stderr) > 80 else f"    Error: {stderr}")
            
            # Determine success (only if we have ground truth)
            if ground_truth:
                success = (prediction == ground_truth)
            elif prediction in ["VALID", "INVALID"]:
                # Got a valid prediction but can't verify
                success = None
            else:
                # Execution failed
                success = False
            
            # Record attempt
            attempt = ReflexionAttempt(
                attempt_number=attempt_num,
                code=code,
                prediction=prediction,
                stdout=stdout,
                stderr=stderr,
                failure_type=failure_type,
                reflection_prompt=None,
                generated_reflection=None,
                timestamp=datetime.now().isoformat()
            )
            attempts.append(attempt)
            
            # Check if we should retry
            if not self._should_retry(failure_type, prediction, ground_truth, attempt_num):
                if self.verbose:
                    print(f"  → Done (no retry needed)")
                break
            
            if self.verbose:
                print(f"  → Generating reflection...")
            
            # ════════════════════════════════════════════════════════════
            # TRUE REFLEXION: Generate reflection and store in memory
            # ════════════════════════════════════════════════════════════
            reflection = self._generate_reflection(
                syllogism_text,
                code or "No code generated",
                failure_type,
                stderr,
                attempt_num,
                prediction=prediction,
                ground_truth=ground_truth
            )
            
            # Store in persistent memory
            reflections_memory.append(f"Attempt {attempt_num}: {reflection}")
            attempt.generated_reflection = reflection
            
            if self.verbose:
                print(f"    Reflection: {reflection[:100]}..." if len(reflection) > 100 else f"    Reflection: {reflection}")
            
            # Build prompt WITH accumulated memory
            reflection_prompt = self._build_reflection_prompt_with_memory(
                syllogism_text,
                code or "No code generated",
                failure_type,
                stderr,
                reflections_memory
            )
            
            attempt.reflection_prompt = reflection_prompt
            
            if self.verbose:
                print(f"  → Generating new code with reflection...")
            
            # Generate new response with full context
            current_response = self._generate_with_reflection(reflection_prompt)
            
            # Small delay to avoid rate limiting
            time.sleep(0.5)
        
        # Determine final results
        final_prediction = attempts[-1].prediction
        
        # First attempt success (only meaningful with ground truth)
        if ground_truth:
            first_attempt_success = (attempts[0].prediction == ground_truth)
            final_success = (final_prediction == ground_truth)
        else:
            first_attempt_success = None
            final_success = None
        
        # Verbose final summary
        if self.verbose:
            success_str = "✓" if final_success else ("?" if final_success is None else "✗")
            print(f"  Result: {success_str} Final={final_prediction} | Attempts={len(attempts)}")
        
        result = ReflexionResult(
            syllogism_id=syllogism_id,
            syllogism_text=syllogism_text,
            ground_truth=ground_truth,
            final_prediction=final_prediction,
            success=final_success,
            total_attempts=len(attempts),
            attempts=attempts,
            first_attempt_success=first_attempt_success,
            reflections_memory=reflections_memory,
            validity=validity,
            plausibility=plausibility
        )
        
        return result
    
    def process_results(self, inference_results: List[Dict]) -> List[Dict]:
        """Process inference results with reflexion"""
        print(f"\nProcessing {len(inference_results)} syllogisms with Reflexion...")
        print(f"Max attempts per syllogism: {self.max_attempts}")
        print(f"Reflexion mode: {self.reflexion_mode.value}")
        if self.verbose:
            print(f"Verbose mode: ON")
        
        reflexion_results = []
        
        # Use tqdm only if not verbose (verbose has its own output)
        if self.verbose:
            iterator = enumerate(inference_results)
        else:
            iterator = enumerate(tqdm(inference_results, desc="Reflexion"))
        
        for i, item in iterator:
            if self.verbose:
                print(f"\n[{i+1}/{len(inference_results)}]", end="")
            
            try:
                result = self._process_single_syllogism(item, item['response'])
                reflexion_results.append(result)
                
                # Save individual logs
                self._save_individual_logs(result)
                
            except Exception as e:
                print(f"\n⚠ Error processing {item['id']}: {e}")
                # Create a failed result
                from datetime import datetime
                failed_result = ReflexionResult(
                    syllogism_id=item['id'],
                    syllogism_text=item.get('text', ''),
                    ground_truth=item.get('label'),
                    final_prediction='ERROR',
                    success=False,
                    total_attempts=0,
                    attempts=[],
                    first_attempt_success=False,
                    reflections_memory=[f"Processing error: {str(e)}"],
                    validity=item.get('validity'),
                    plausibility=item.get('plausibility')
                )
                reflexion_results.append(failed_result)
            
            # Add small delay between syllogisms to avoid rate limiting
            # Every 10 syllogisms, add a longer pause
            if (i + 1) % 10 == 0:
                if self.verbose:
                    print(f"\n    [Pause 2s to avoid rate limiting...]")
                time.sleep(2.0)
            else:
                time.sleep(0.3)  # Small delay between each
        
        # Generate statistics and summary
        self._generate_statistics(reflexion_results)
        self._generate_summary(reflexion_results)
        self._generate_simple_report(reflexion_results)
        
        # Generate validity/plausibility breakdown (if data available)
        has_validity_data = any(r.validity is not None for r in reflexion_results)
        if has_validity_data:
            self._generate_validity_plausibility_breakdown(reflexion_results)
        
        # Analyze failures for training data (where ground truth is available)
        has_ground_truth = any(r.ground_truth is not None for r in reflexion_results)
        if has_ground_truth:
            self._analyze_failures(reflexion_results)
            # Generate learned patterns summary from failure analysis
            self._generate_learned_patterns(reflexion_results)
        
        # Convert to predictions format
        predictions = []
        for result in reflexion_results:
            predictions.append({
                'id': result.syllogism_id,
                'prediction': result.final_prediction,
                'label': result.ground_truth
            })
        
        print(f"\n✓ Reflexion complete")
        print(f"✓ Logs and programs saved to: {self.execution_dir}")
        
        # Show Bedrock call statistics
        try:
            bedrock_stats = self.client.get_stats()
            print(f"✓ Bedrock calls: {bedrock_stats['total_calls']} (retries: {bedrock_stats['total_retries']})")
        except:
            pass
        
        return predictions
    
    def _save_individual_logs(self, result: ReflexionResult):
        """Save detailed logs for one syllogism"""
        # JSON log
        json_file = os.path.join(self.logs_dir, f"{result.syllogism_id}.json")
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(result.to_dict(), f, indent=2)
        
        # Text log
        txt_file = os.path.join(self.logs_dir, f"{result.syllogism_id}.txt")
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write(f"TRUE REFLEXION LOG - {result.syllogism_id}\n")
            f.write(f"Mode: {self.reflexion_mode.value}\n")
            f.write("=" * 80 + "\n\n")
            
            f.write(f"Syllogism:\n{result.syllogism_text}\n\n")
            
            if result.ground_truth:
                f.write(f"Ground Truth: {result.ground_truth}\n")
            else:
                f.write(f"Ground Truth: [NOT AVAILABLE - test data]\n")
            
            # Add validity and plausibility for training data
            if result.validity is not None:
                f.write(f"Validity: {result.validity}\n")
            if result.plausibility is not None:
                f.write(f"Plausibility: {result.plausibility}\n")
            
            f.write(f"Final Prediction: {result.final_prediction}\n")
            
            if result.success is not None:
                f.write(f"Success: {result.success}\n")
            else:
                f.write(f"Success: [UNKNOWN - no ground truth]\n")
            
            f.write(f"Total Attempts: {result.total_attempts}\n")
            f.write(f"Total Reflections Generated: {len(result.reflections_memory)}\n\n")
            
            # Show accumulated memory
            if result.reflections_memory:
                f.write("=" * 80 + "\n")
                f.write("ACCUMULATED REFLECTIONS MEMORY\n")
                f.write("=" * 80 + "\n")
                for i, reflection in enumerate(result.reflections_memory, 1):
                    f.write(f"\n[Memory {i}] {reflection}\n")
                f.write("\n")
            
            for attempt in result.attempts:
                f.write("-" * 80 + "\n")
                f.write(f"ATTEMPT {attempt.attempt_number}\n")
                f.write("-" * 80 + "\n")
                f.write(f"Prediction: {attempt.prediction}\n")
                f.write(f"Failure Type: {attempt.failure_type.value}\n\n")
                
                if attempt.code:
                    f.write("Code:\n")
                    f.write(attempt.code + "\n\n")
                
                if attempt.stdout:
                    f.write(f"Stdout: {attempt.stdout}\n\n")
                
                if attempt.stderr:
                    f.write(f"Stderr: {attempt.stderr}\n\n")
                
                if attempt.generated_reflection:
                    f.write("=" * 40 + "\n")
                    f.write("LLM-GENERATED REFLECTION:\n")
                    f.write("=" * 40 + "\n")
                    f.write(attempt.generated_reflection + "\n\n")
                
                if attempt.reflection_prompt:
                    f.write("Reflection Prompt (with memory):\n")
                    f.write("-" * 40 + "\n")
                    f.write(attempt.reflection_prompt + "\n\n")
    
    def _generate_statistics(self, results: List[ReflexionResult]):
        """Generate aggregate statistics including reflection metrics"""
        total = len(results)
        
        # Handle cases where ground truth may not be available
        results_with_gt = [r for r in results if r.ground_truth is not None]
        total_with_gt = len(results_with_gt)
        
        successful = sum(1 for r in results_with_gt if r.success)
        first_attempt_success = sum(1 for r in results_with_gt if r.first_attempt_success)
        
        # Attempts distribution
        attempts_dist = {}
        for r in results:
            attempts_dist[r.total_attempts] = attempts_dist.get(r.total_attempts, 0) + 1
        
        # Failure types
        failure_types = {}
        for r in results:
            for attempt in r.attempts:
                ft = attempt.failure_type.value
                failure_types[ft] = failure_types.get(ft, 0) + 1
        
        # Reflexion helped (only meaningful with ground truth)
        reflexion_helped = sum(
            1 for r in results_with_gt 
            if not r.first_attempt_success and r.success
        )
        
        # Reflection metrics
        total_reflections_generated = sum(len(r.reflections_memory) for r in results)
        
        successful_with_retries = [
            r for r in results_with_gt 
            if r.success and not r.first_attempt_success
        ]
        avg_reflections_per_success = (
            sum(len(r.reflections_memory) for r in successful_with_retries) / len(successful_with_retries)
            if successful_with_retries else 0
        )
        
        reflection_lengths = []
        for r in results:
            for attempt in r.attempts:
                if attempt.generated_reflection:
                    reflection_lengths.append(len(attempt.generated_reflection))
        
        avg_reflection_length = sum(reflection_lengths) / len(reflection_lengths) if reflection_lengths else 0
        
        stats = {
            'total_syllogisms': total,
            'total_with_ground_truth': total_with_gt,
            'successful': successful,
            'success_rate': successful / total_with_gt if total_with_gt > 0 else None,
            'first_attempt_success': first_attempt_success,
            'first_attempt_success_rate': first_attempt_success / total_with_gt if total_with_gt > 0 else None,
            'reflexion_helped': reflexion_helped,
            'reflexion_improvement_rate': (
                reflexion_helped / (total_with_gt - first_attempt_success) 
                if (total_with_gt - first_attempt_success) > 0 else None
            ),
            'attempts_distribution': attempts_dist,
            'failure_types': failure_types,
            'reflexion_mode': self.reflexion_mode.value,
            'total_reflections_generated': total_reflections_generated,
            'avg_reflections_per_success': round(avg_reflections_per_success, 2),
            'avg_reflection_length': round(avg_reflection_length, 1),
            'min_reflection_length': min(reflection_lengths) if reflection_lengths else 0,
            'max_reflection_length': max(reflection_lengths) if reflection_lengths else 0
        }
        
        stats_file = os.path.join(self.execution_dir, 'statistics.json')
        with open(stats_file, 'w') as f:
            json.dump(stats, f, indent=2)
    
    def _generate_summary(self, results: List[ReflexionResult]):
        """Generate human-readable summary"""
        summary_file = os.path.join(self.execution_dir, 'summary.txt')
        
        total = len(results)
        results_with_gt = [r for r in results if r.ground_truth is not None]
        total_with_gt = len(results_with_gt)
        
        successful = sum(1 for r in results_with_gt if r.success)
        first_attempt_success = sum(1 for r in results_with_gt if r.first_attempt_success)
        reflexion_helped = sum(1 for r in results_with_gt if not r.first_attempt_success and r.success)
        total_reflections = sum(len(r.reflections_memory) for r in results)
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("TRUE REFLEXION EXECUTION SUMMARY\n")
            f.write("(with LLM-generated reflections and persistent memory)\n")
            f.write("=" * 80 + "\n\n")
            
            f.write(f"Reflexion Mode: {self.reflexion_mode.value}\n")
            f.write(f"Total Syllogisms: {total}\n")
            
            if total_with_gt > 0:
                f.write(f"With Ground Truth: {total_with_gt}\n")
                f.write(f"Successful: {successful} ({successful/total_with_gt*100:.1f}%)\n")
                f.write(f"First Attempt Success: {first_attempt_success} ({first_attempt_success/total_with_gt*100:.1f}%)\n")
                f.write(f"Fixed by Reflexion: {reflexion_helped}\n")
            else:
                f.write(f"⚠ No ground truth available - cannot compute accuracy\n")
            
            f.write("\n")
            
            f.write("=" * 80 + "\n")
            f.write("REFLECTION METRICS\n")
            f.write("=" * 80 + "\n")
            f.write(f"Total Reflections Generated: {total_reflections}\n")
            
            successful_with_retries = [r for r in results_with_gt if r.success and not r.first_attempt_success]
            if successful_with_retries:
                avg_reflections = sum(len(r.reflections_memory) for r in successful_with_retries) / len(successful_with_retries)
                f.write(f"Avg Reflections per Success (with retries): {avg_reflections:.1f}\n")
            
            reflection_lengths = []
            for r in results:
                for attempt in r.attempts:
                    if attempt.generated_reflection:
                        reflection_lengths.append(len(attempt.generated_reflection))
            
            if reflection_lengths:
                f.write(f"Avg Reflection Length: {sum(reflection_lengths)/len(reflection_lengths):.0f} chars\n")
            
            f.write("\n")
            
            f.write("Attempts Distribution:\n")
            attempts_dist = {}
            for r in results:
                attempts_dist[r.total_attempts] = attempts_dist.get(r.total_attempts, 0) + 1
            for attempts, count in sorted(attempts_dist.items()):
                f.write(f"  {attempts} attempt(s): {count}\n")
            
            # Sample reflections
            f.write("\n" + "=" * 80 + "\n")
            f.write("SAMPLE GENERATED REFLECTIONS\n")
            f.write("=" * 80 + "\n")
            
            sample_count = 0
            for r in results:
                if r.reflections_memory and sample_count < 3:
                    f.write(f"\n[{r.syllogism_id}]\n")
                    for reflection in r.reflections_memory[:2]:
                        f.write(f"  • {reflection[:200]}...\n" if len(reflection) > 200 else f"  • {reflection}\n")
                    sample_count += 1
            
            f.write("\n" + "=" * 80 + "\n")

    def _generate_simple_report(self, results: List[ReflexionResult]):
        """Generate a simple execution report with key counts"""
        report_file = os.path.join(self.execution_dir, 'simple_report.txt')
        
        total = len(results)
        valid_count = sum(1 for r in results if r.final_prediction == 'VALID')
        invalid_count = sum(1 for r in results if r.final_prediction == 'INVALID')
        error_count = sum(1 for r in results if r.final_prediction not in ('VALID', 'INVALID'))
        
        # Count error types across all attempts
        runtime_errors = 0
        syntax_errors = 0
        for r in results:
            for attempt in r.attempts:
                if attempt.failure_type.value == 'runtime_error':
                    runtime_errors += 1
                elif attempt.failure_type.value == 'syntax_error':
                    syntax_errors += 1
        
        # Count plausibility (training data only)
        plausible_count = sum(1 for r in results if r.plausibility is True)
        implausible_count = sum(1 for r in results if r.plausibility is False)
        has_plausibility = plausible_count > 0 or implausible_count > 0
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("SIMPLE EXECUTION REPORT\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Total Syllogisms Processed: {total}\n\n")
            f.write("Predictions:\n")
            f.write(f"  VALID:   {valid_count}\n")
            f.write(f"  INVALID: {invalid_count}\n")
            f.write(f"  ERROR:   {error_count}\n\n")
            f.write("Prolog Errors Breakdown:\n")
            f.write(f"  Runtime Errors: {runtime_errors}\n")
            f.write(f"  Syntax Errors:  {syntax_errors}\n\n")
            
            if has_plausibility:
                f.write("Ground Truth Plausibility:\n")
                f.write(f"  Plausible:   {plausible_count}\n")
                f.write(f"  Implausible: {implausible_count}\n\n")
            
            f.write("=" * 80 + "\n")
        
        print(f"✓ Simple report saved to: {report_file}")

    def _generate_validity_plausibility_breakdown(self, results: List[ReflexionResult]):
        """Generate detailed breakdown by validity/plausibility combinations."""
        breakdown_file = os.path.join(self.execution_dir, 'validity_plausibility_breakdown.txt')
        breakdown_json = os.path.join(self.execution_dir, 'validity_plausibility_breakdown.json')
        
        combinations = {
            'valid_plausible': {'total': 0, 'correct': 0, 'items': []},
            'valid_implausible': {'total': 0, 'correct': 0, 'items': []},
            'invalid_plausible': {'total': 0, 'correct': 0, 'items': []},
            'invalid_implausible': {'total': 0, 'correct': 0, 'items': []}
        }
        
        for r in results:
            if r.validity is None or r.plausibility is None:
                continue
            
            if r.validity and r.plausibility:
                key = 'valid_plausible'
            elif r.validity and not r.plausibility:
                key = 'valid_implausible'
            elif not r.validity and r.plausibility:
                key = 'invalid_plausible'
            else:
                key = 'invalid_implausible'
            
            combinations[key]['total'] += 1
            
            predicted_valid = r.final_prediction == 'VALID'
            is_correct = predicted_valid == r.validity
            
            if is_correct:
                combinations[key]['correct'] += 1
            
            combinations[key]['items'].append({
                'id': r.syllogism_id,
                'ground_truth_validity': r.validity,
                'ground_truth_plausibility': r.plausibility,
                'predicted': r.final_prediction,
                'correct': is_correct,
                'attempts': r.total_attempts
            })
        
        for key in combinations:
            total = combinations[key]['total']
            correct = combinations[key]['correct']
            combinations[key]['accuracy'] = (correct / total * 100) if total > 0 else 0.0
        
        with open(breakdown_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("VALIDITY / PLAUSIBILITY BREAKDOWN\n")
            f.write(f"Reflexion Mode: {self.reflexion_mode.value}\n")
            f.write("=" * 80 + "\n\n")
            
            f.write("Combinations:\n")
            f.write("- VP: Valid + Plausible\n")
            f.write("- VI: Valid + Implausible\n")
            f.write("- IP: Invalid + Plausible\n")
            f.write("- II: Invalid + Implausible\n\n")
            
            f.write(f"{'Combination':<25} {'Total':<10} {'Correct':<10} {'Accuracy':<10}\n")
            f.write("-" * 55 + "\n")
            
            labels = {
                'valid_plausible': 'Valid + Plausible (VP)',
                'valid_implausible': 'Valid + Implausible (VI)',
                'invalid_plausible': 'Invalid + Plausible (IP)',
                'invalid_implausible': 'Invalid + Implausible (II)'
            }
            
            total_all = 0
            correct_all = 0
            
            for key, label in labels.items():
                data = combinations[key]
                total_all += data['total']
                correct_all += data['correct']
                f.write(f"{label:<25} {data['total']:<10} {data['correct']:<10} {data['accuracy']:.1f}%\n")
            
            f.write("-" * 55 + "\n")
            overall_acc = (correct_all / total_all * 100) if total_all > 0 else 0.0
            f.write(f"{'OVERALL':<25} {total_all:<10} {correct_all:<10} {overall_acc:.1f}%\n")
        
        json_data = {
            'reflexion_mode': self.reflexion_mode.value,
            'summary': {
                'total': total_all,
                'correct': correct_all,
                'overall_accuracy': overall_acc
            },
            'combinations': {
                key: {
                    'label': labels[key],
                    'total': combinations[key]['total'],
                    'correct': combinations[key]['correct'],
                    'accuracy': combinations[key]['accuracy'],
                    'items': combinations[key]['items']
                }
                for key in labels
            }
        }
        
        with open(breakdown_json, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2)
        
        print(f"✓ Validity/Plausibility breakdown saved to: {breakdown_file}")
        
        return combinations


    def _analyze_failures(self, results: List[ReflexionResult]):
        """
        Analyze all failed predictions using LLM and generate a comprehensive report.
        Only runs for training data where ground truth is available.
        """
        # Filter for failures (prediction != ground truth)
        failures = [r for r in results if r.ground_truth and r.final_prediction != r.ground_truth]
        
        if not failures:
            print("✓ No failures to analyze (all predictions correct)")
            return
        
        print(f"\n{'='*80}")
        print(f"FAILURE ANALYSIS: Analyzing {len(failures)} incorrect predictions...")
        print(f"{'='*80}")
        
        # Load the analysis prompt
        analysis_prompt = self._load_failure_analysis_prompt()
        
        # Create the report file
        report_file = os.path.join(self.execution_dir, 'failure_analysis_report.txt')
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("FAILURE ANALYSIS REPORT\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Failures Analyzed: {len(failures)}\n")
            f.write(f"Reflexion Mode: {self.reflexion_mode.value}\n")
            f.write("=" * 80 + "\n\n")
        
        for i, result in enumerate(failures, 1):
            print(f"  [{i}/{len(failures)}] Analyzing {result.syllogism_id}...", end=" ")
            
            try:
                # Build the log content for analysis
                log_content = self._build_log_for_analysis(result)
                
                # Call LLM for analysis
                user_prompt = f"""## Now Analyze This Log

Read the provided reflexion log file and produce your analysis following the format above.

Focus especially on:
1. Whether the model misunderstood VALID vs INVALID
2. Whether plausibility influenced the prediction
3. The specific code error that caused the wrong result
4. What the correct code should have been

---

## REFLEXION LOG FILE

{log_content}
"""
                
                analysis = self.client.generate(
                    prompt=user_prompt,
                    system_prompt=analysis_prompt,
                    temperature=0.3
                )
                
                # Append to report file
                with open(report_file, 'a', encoding='utf-8') as f:
                    f.write("\n" + "=" * 80 + "\n")
                    f.write(f"CASE {i}: {result.syllogism_id}\n")
                    f.write("=" * 80 + "\n\n")
                    f.write(f"Syllogism: {result.syllogism_text}\n\n")
                    f.write(f"Ground Truth Validity: {'VALID' if result.validity else 'INVALID'}\n")
                    f.write(f"Ground Truth Plausibility: {'PLAUSIBLE' if result.plausibility else 'IMPLAUSIBLE'}\n")
                    f.write(f"Prediction: {result.final_prediction}\n")
                    f.write(f"Ground Truth Label: {result.ground_truth}\n\n")
                    f.write("-" * 80 + "\n")
                    f.write("LLM ANALYSIS:\n")
                    f.write("-" * 80 + "\n\n")
                    f.write(analysis + "\n")
                
                print("✓")
                
                # Rate limiting
                time.sleep(1.0)
                
            except Exception as e:
                print(f"✗ Error: {e}")
                with open(report_file, 'a', encoding='utf-8') as f:
                    f.write("\n" + "=" * 80 + "\n")
                    f.write(f"CASE {i}: {result.syllogism_id}\n")
                    f.write("=" * 80 + "\n\n")
                    f.write(f"Syllogism: {result.syllogism_text}\n")
                    f.write(f"Ground Truth: {result.ground_truth}\n")
                    f.write(f"Prediction: {result.final_prediction}\n\n")
                    f.write(f"ERROR: Failed to analyze - {str(e)}\n")
        
        print(f"\n✓ Failure analysis report saved to: {report_file}")
    
    def _load_failure_analysis_prompt(self) -> str:
        """Load the failure analysis prompt from file"""
        prompt_file = os.path.join(os.path.dirname(__file__), 'prompts', 'failure_analysis.txt')
        
        if os.path.exists(prompt_file):
            with open(prompt_file, 'r', encoding='utf-8') as f:
                return f.read()
        
        # Fallback inline prompt
        return """You are an expert in formal logic and syllogistic reasoning. 
Analyze why the Prolog-based syllogism solver produced an incorrect prediction.
Identify the root cause: Logic Error, Encoding Error, Plausibility Bias, or PySwip Error.
Explain what went wrong and how to fix it."""
    
    def _build_log_for_analysis(self, result: ReflexionResult) -> str:
        """Build a formatted log string for LLM analysis"""
        lines = []
        lines.append(f"Syllogism ID: {result.syllogism_id}")
        lines.append(f"Syllogism Text: {result.syllogism_text}")
        lines.append("")
        lines.append(f"Ground Truth Validity: {'VALID' if result.validity else 'INVALID'}")
        lines.append(f"Ground Truth Plausibility: {'PLAUSIBLE' if result.plausibility else 'IMPLAUSIBLE'}")
        lines.append(f"Ground Truth Label: {result.ground_truth}")
        lines.append(f"Final Prediction: {result.final_prediction}")
        lines.append(f"Total Attempts: {result.total_attempts}")
        lines.append("")
        
        for attempt in result.attempts:
            lines.append(f"--- ATTEMPT {attempt.attempt_number} ---")
            lines.append(f"Prediction: {attempt.prediction}")
            lines.append(f"Failure Type: {attempt.failure_type.value}")
            lines.append("")
            
            if attempt.code:
                lines.append("Generated Code:")
                lines.append("```prolog")
                lines.append(attempt.code)
                lines.append("```")
                lines.append("")
            
            if attempt.stdout:
                lines.append(f"Stdout: {attempt.stdout}")
            
            if attempt.stderr:
                lines.append(f"Stderr: {attempt.stderr}")
                lines.append("")
            
            if attempt.generated_reflection:
                lines.append("LLM Reflection:")
                lines.append(attempt.generated_reflection)
                lines.append("")
        
        if result.reflections_memory:
            lines.append("--- ACCUMULATED REFLECTIONS MEMORY ---")
            for i, mem in enumerate(result.reflections_memory, 1):
                lines.append(f"[Memory {i}]: {mem}")
            lines.append("")
        
        return "\n".join(lines)


    def _generate_learned_patterns(self, results: List[ReflexionResult]):
        """
        After failure analysis, generate a summary of learned patterns.
        This summary can be appended to the Prolog prompt for test phase.
        """
        # Check if failure analysis report exists
        failure_report_file = os.path.join(self.execution_dir, 'failure_analysis_report.txt')
        
        if not os.path.exists(failure_report_file):
            print("⚠ No failure analysis report found, skipping pattern summary")
            return
        
        # Read the failure analysis report
        with open(failure_report_file, 'r', encoding='utf-8') as f:
            failure_report = f.read()
        
        # Check if there are actual analyses (not just errors)
        if "LLM ANALYSIS:" not in failure_report:
            print("⚠ No successful analyses in report, skipping pattern summary")
            return
        
        print(f"\n{'='*80}")
        print("GENERATING LEARNED PATTERNS SUMMARY...")
        print(f"{'='*80}")
        
        # Load the summarizer prompt
        summarizer_prompt = self._load_pattern_summarizer_prompt()
        
        try:
            # Call LLM to summarize patterns
            user_prompt = f"""## Failure Analysis Report to Summarize

{failure_report}

---

Now produce the Learned Failure Patterns Summary following the format specified.
"""
            
            summary = self.client.generate(
                prompt=user_prompt,
                system_prompt=summarizer_prompt,
                temperature=0.3
            )
            
            # Save the learned patterns
            patterns_file = os.path.join(self.execution_dir, 'learned_patterns.txt')
            
            with open(patterns_file, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("LEARNED FAILURE PATTERNS\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("Use this to augment the Prolog prompt during test phase\n")
                f.write("=" * 80 + "\n\n")
                f.write(summary)
            
            print(f"✓ Learned patterns saved to: {patterns_file}")
            print("\n  → Use this file to augment your Prolog prompt for test phase")
            
        except Exception as e:
            print(f"✗ Failed to generate pattern summary: {e}")
    
    def _load_pattern_summarizer_prompt(self) -> str:
        """Load the pattern summarizer prompt from file"""
        prompt_file = os.path.join(os.path.dirname(__file__), 'prompts', 'failure_pattern_summarizer.txt')
        
        if os.path.exists(prompt_file):
            with open(prompt_file, 'r', encoding='utf-8') as f:
                return f.read()
        
        # Fallback inline prompt
        return """You are an expert in formal logic. Analyze the failure report and extract:
1. Recurring failure patterns
2. Root cause categories  
3. Specific rules violated
4. Actionable lessons

Output a summary with patterns, checklist, and code fixes needed."""
