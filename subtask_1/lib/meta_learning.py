"""
Meta-Learning from Errors System

This module implements a three-phase pipeline:
1. Training Phase: Run on training data, collect all errors
2. Analysis Phase: Analyze error patterns, generate insights using LLM
3. Test Phase: Use enhanced prompt with error-derived few-shots and guidelines
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from tqdm import tqdm


class MetaLearningLogger:
    """Logger for the meta-learning pipeline."""
    
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create log file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.output_dir / f"meta_learning_log_{timestamp}.txt"
        
        # Setup logger
        self.logger = logging.getLogger(f"MetaLearning_{timestamp}")
        self.logger.setLevel(logging.DEBUG)
        
        # Clear existing handlers
        self.logger.handlers = []
        
        # File handler - detailed logs
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        
        # Console handler - summary only
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(message)s')
        console_handler.setFormatter(console_formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # Initialize phase tracking
        self.current_phase = None
        self.phase_stats = {}
    
    def start_phase(self, phase_name: str):
        """Log phase start."""
        self.current_phase = phase_name
        self.phase_stats[phase_name] = {"start_time": datetime.now()}
        
        self.logger.info("=" * 70)
        self.logger.info(f"PHASE: {phase_name}")
        self.logger.info("=" * 70)
    
    def end_phase(self, summary: dict = None):
        """Log phase end with summary."""
        if self.current_phase:
            self.phase_stats[self.current_phase]["end_time"] = datetime.now()
            duration = self.phase_stats[self.current_phase]["end_time"] - \
                       self.phase_stats[self.current_phase]["start_time"]
            
            self.logger.info(f"Phase completed in {duration}")
            
            if summary:
                self.phase_stats[self.current_phase]["summary"] = summary
                for key, value in summary.items():
                    self.logger.info(f"  {key}: {value}")
            
            self.logger.info("-" * 70)
    
    def log_error(self, error_data: dict):
        """Log individual error details."""
        self.logger.debug(f"""
ERROR DETECTED:
  ID: {error_data.get('id', 'N/A')}
  Type: {error_data.get('type', 'N/A')}
  Syllogism: {error_data.get('syllogism', 'N/A')[:100]}...
  Ground Truth: {error_data.get('ground_truth', 'N/A')}
  Prediction: {error_data.get('prediction', 'N/A')}
  Extracted Form: {error_data.get('extracted_structure', {}).get('form', 'N/A') if error_data.get('extracted_structure') else 'N/A'}
  Plausibility: {error_data.get('plausibility', 'N/A')}
""")
    
    def log_analysis_result(self, analysis: dict):
        """Log error analysis results."""
        self.logger.info(f"Error Patterns Found: {len(analysis.get('error_patterns', []))}")
        for pattern in analysis.get('error_patterns', []):
            self.logger.debug(f"  - {pattern.get('pattern_name', 'Unknown')}: {pattern.get('description', '')}")
        
        self.logger.info(f"Few-Shot Examples Generated: {len(analysis.get('few_shot_examples', []))}")
        self.logger.info(f"Warning Signs Identified: {len(analysis.get('warning_signs', []))}")
        self.logger.info(f"New Guidelines Added: {len(analysis.get('new_guidelines', []))}")
    
    def log_prompt_enhancement(self, original_length: int, enhanced_length: int):
        """Log prompt enhancement details."""
        added = enhanced_length - original_length
        self.logger.info(f"Prompt Enhanced:")
        self.logger.info(f"  Original length: {original_length} chars")
        self.logger.info(f"  Enhanced length: {enhanced_length} chars")
        self.logger.info(f"  Added: {added} chars ({added/original_length*100:.1f}% increase)")
    
    def log_enhanced_prompt_content(self, enhanced_prompt: str, analysis: dict = None):
        """Log the full enhanced prompt content to the debug log."""
        self.logger.debug("=" * 70)
        self.logger.debug("ENHANCED PROMPT CONTENT (for test phase)")
        self.logger.debug("=" * 70)
        
        if analysis:
            few_shots = analysis.get("few_shot_examples", [])
            warnings = analysis.get("warning_signs", [])
            guidelines = analysis.get("new_guidelines", [])
            
            self.logger.debug(f"Enhancements included:")
            self.logger.debug(f"  - {len(few_shots)} few-shot examples")
            self.logger.debug(f"  - {len(warnings)} warning signs")
            self.logger.debug(f"  - {len(guidelines)} new guidelines")
        
        self.logger.debug("-" * 70)
        self.logger.debug("FULL PROMPT:")
        self.logger.debug("-" * 70)
        
        # Log the full prompt (split into lines for readability)
        for line in enhanced_prompt.split('\n'):
            self.logger.debug(line)
        
        self.logger.debug("=" * 70)
        self.logger.debug("END OF ENHANCED PROMPT")
        self.logger.debug("=" * 70)
    
    def info(self, message: str):
        """Log info message."""
        self.logger.info(message)
    
    def debug(self, message: str):
        """Log debug message."""
        self.logger.debug(message)
    
    def save_final_report(self) -> Path:
        """Generate and save final report."""
        report_file = self.output_dir / "meta_learning_report.md"
        
        report = f"""# Meta-Learning Pipeline Report

Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Phase Summary

"""
        for phase, stats in self.phase_stats.items():
            duration = stats.get("end_time", datetime.now()) - stats["start_time"]
            report += f"### {phase}\n"
            report += f"- Duration: {duration}\n"
            if "summary" in stats:
                for key, value in stats["summary"].items():
                    report += f"- {key}: {value}\n"
            report += "\n"
        
        report += f"""
## Files Generated

- Error Log: `error_log.json`
- Error Analysis: `error_analysis.json`
- Enhanced Prompt: `enhanced_structure_extraction.txt`
- Predictions: `predictions.json`
- This Report: `meta_learning_report.md`
- Full Log: `{self.log_file.name}`
"""
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        self.logger.info(f"Final report saved to: {report_file}")
        
        return report_file


class ErrorAnalyzer:
    """Analyzes training errors to generate insights for test phase."""
    
    def __init__(self, llm_client, prompt_dir: str = "prompts"):
        self.llm_client = llm_client
        self.prompt_dir = prompt_dir
        self.analysis_prompt = self._load_analysis_prompt()
    
    def _load_analysis_prompt(self) -> str:
        """Load the error analysis prompt."""
        prompt_path = os.path.join(self.prompt_dir, "error_analysis.txt")
        if os.path.exists(prompt_path):
            print(f"  ✓ Loaded error analysis prompt from: {prompt_path}")
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            print(f"  ⚠ Prompt file not found at: {prompt_path}, using default")
            # Return default prompt
            return self._get_default_prompt()
    
    def _get_default_prompt(self) -> str:
        """Return default error analysis prompt."""
        return '''You are an expert in formal logic and syllogistic reasoning. Analyze these errors from a syllogism validity prediction system.

The system extracts syllogism structure (premises, conclusion, mood, figure) and then uses formal logic rules to determine validity. Errors occur when:
1. The structure is extracted incorrectly
2. The middle term is misidentified
3. The figure is calculated wrong
4. Proposition types (A/E/I/O) are misclassified

## Errors to Analyze

{errors}

## Your Task

Analyze these errors and provide:

### 1. Error Pattern Categories

Group the errors by their root cause. Common patterns include:
- Premise/Conclusion Confusion: The conclusion was mistaken for a premise or vice versa
- Figure Calculation Error: The middle term position was misidentified, leading to wrong figure
- Proposition Type Error: A/E/I/O classification was wrong
- Middle Term Error: Wrong term identified as the middle term
- Complex Term Handling: Phrases like "anything that is X" not properly simplified
- Negation Handling: Double negatives or "not all" misinterpreted

For each pattern, explain:
- What went wrong
- How to detect this pattern
- How to fix it

### 2. Corrected Examples (Few-Shots)

For the most instructive errors, provide the CORRECT extraction. These will be used as few-shot examples.

Format each example with:
- The original syllogism
- What mistake was likely made
- The correct extraction with reasoning
- The correct validity judgment

### 3. Warning Signs

List specific phrases or patterns that should trigger extra caution:
- Phrases that often cause premise/conclusion confusion
- Complex term structures that need simplification
- Ambiguous wordings

### 4. Updated Guidelines

Write specific guidelines to add to the extraction prompt to prevent these errors.

## Output Format

Return valid JSON with this structure:

- "error_patterns": array of objects with pattern_name, description, frequency, detection, fix
- "few_shot_examples": array of objects with syllogism, correct_extraction, reasoning, validity, common_mistake
- "warning_signs": array of objects with pattern, risk, action
- "new_guidelines": array of strings

IMPORTANT: Return ONLY valid JSON. Do not include any text before or after the JSON.'''
    
    def analyze(self, error_log: dict, max_errors: int = 20) -> dict:
        """
        Analyze errors and generate:
        1. Error pattern categories
        2. Root causes
        3. Few-shot examples
        4. Prompt guidelines
        """
        errors = error_log.get("errors", [])
        
        if not errors:
            return {
                "error_patterns": [],
                "few_shot_examples": [],
                "warning_signs": [],
                "new_guidelines": []
            }
        
        # Limit errors for analysis (to fit in context)
        errors_to_analyze = errors[:max_errors]
        
        # Prepare error summary for LLM
        error_summary = self._prepare_error_summary(errors_to_analyze)
        
        # Build prompt
        prompt = self.analysis_prompt.format(errors=error_summary)
        
        # Call LLM to analyze
        try:
            response = self.llm_client.generate(
                prompt=prompt,
                temperature=0.0,
                max_tokens=4000
            )
            
            # Parse analysis
            analysis = self._parse_analysis(response)
            
        except Exception as e:
            print(f"Error during LLM analysis: {e}")
            # Return empty analysis on error
            analysis = {
                "error_patterns": [],
                "few_shot_examples": [],
                "warning_signs": [],
                "new_guidelines": [],
                "raw_error": str(e)
            }
        
        return analysis
    
    def _prepare_error_summary(self, errors: List[dict]) -> str:
        """Format errors for LLM analysis."""
        summary_parts = []
        
        for i, error in enumerate(errors, 1):
            structure = error.get("extracted_structure", {})
            form = structure.get("form", "N/A") if structure else "N/A"
            
            summary_parts.append(f"""
### Error {i}: {error.get("type", "UNKNOWN")}

**Syllogism:** {error.get("syllogism", "N/A")}

**Ground Truth:** {error.get("ground_truth", "N/A")}
**Prediction:** {error.get("prediction", "N/A")}
**Extracted Form:** {form}
**Plausibility:** {error.get("plausibility", "N/A")}

**Self-Consistency Info:**
{json.dumps(error.get("self_consistency", {}), indent=2) if error.get("self_consistency") else "N/A"}
""")
        
        return "\n".join(summary_parts)
    
    def _parse_analysis(self, response: str) -> dict:
        """Parse LLM analysis response."""
        # Try to extract JSON from response
        try:
            # Look for JSON block
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            elif "```" in response:
                json_start = response.find("```") + 3
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            else:
                # Try to find JSON object directly
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                json_str = response[json_start:json_end]
            
            analysis = json.loads(json_str)
            
            # Ensure all required keys exist
            analysis.setdefault("error_patterns", [])
            analysis.setdefault("few_shot_examples", [])
            analysis.setdefault("warning_signs", [])
            analysis.setdefault("new_guidelines", [])
            
            return analysis
            
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Failed to parse JSON from response: {e}")
            # Return structured response with raw text
            return {
                "error_patterns": [],
                "few_shot_examples": [],
                "warning_signs": [],
                "new_guidelines": [],
                "raw_response": response,
                "parse_error": str(e)
            }


class PromptEnhancer:
    """Enhances base prompts with error-derived insights."""
    
    def __init__(self, base_prompt_path: str):
        self.base_prompt_path = base_prompt_path
        self.base_prompt = self._load_prompt(base_prompt_path)
    
    def _load_prompt(self, path: str) -> str:
        """Load prompt from file."""
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def enhance(self, error_analysis: dict, max_few_shots: int = 5) -> str:
        """
        Generate enhanced prompt by adding:
        1. Few-shot examples from corrected errors
        2. Warning signs section
        3. New guidelines
        """
        enhanced = self.base_prompt
        
        # Add few-shot examples (limit to max_few_shots)
        few_shots = error_analysis.get("few_shot_examples", [])[:max_few_shots]
        if few_shots:
            few_shots_section = self._format_few_shots(few_shots)
            # Insert before existing examples or at a good location
            if "## WORKED EXAMPLE" in enhanced:
                enhanced = enhanced.replace(
                    "## WORKED EXAMPLE",
                    f"{few_shots_section}\n\n## WORKED EXAMPLE"
                )
            elif "## Example" in enhanced:
                enhanced = enhanced.replace(
                    "## Example",
                    f"{few_shots_section}\n\n## Example"
                )
            else:
                # Add before the output format section
                if "## Output Format" in enhanced:
                    enhanced = enhanced.replace(
                        "## Output Format",
                        f"{few_shots_section}\n\n## Output Format"
                    )
                else:
                    enhanced = enhanced + "\n\n" + few_shots_section
        
        # Add warning signs
        warnings = error_analysis.get("warning_signs", [])
        if warnings:
            warnings_section = self._format_warnings(warnings)
            if "## Important" in enhanced:
                enhanced = enhanced.replace(
                    "## Important",
                    f"{warnings_section}\n\n## Important"
                )
            else:
                # Add near the end
                enhanced = enhanced + "\n\n" + warnings_section
        
        # Add new guidelines
        guidelines = error_analysis.get("new_guidelines", [])
        if guidelines:
            guidelines_section = self._format_guidelines(guidelines)
            if "Now extract" in enhanced:
                enhanced = enhanced.replace(
                    "Now extract",
                    f"{guidelines_section}\n\nNow extract"
                )
            else:
                enhanced = enhanced + "\n\n" + guidelines_section
        
        return enhanced
    
    def _format_few_shots(self, examples: list) -> str:
        """Format few-shot examples from errors."""
        output = "## ⚠️ ERROR-DERIVED EXAMPLES (Pay Special Attention!)\n\n"
        output += "These examples come from common mistakes. Study them carefully.\n\n"
        
        for i, ex in enumerate(examples, 1):
            output += f"### Tricky Example {i}\n\n"
            output += f"**Input:** \"{ex.get('syllogism', 'N/A')}\"\n\n"
            
            if ex.get('common_mistake'):
                output += f"**Common Mistake:** {ex['common_mistake']}\n\n"
            
            output += f"**Correct Analysis:**\n"
            output += f"- This syllogism is **{ex.get('validity', 'N/A')}**\n"
            output += f"- Reasoning: {ex.get('reasoning', 'N/A')}\n\n"
            
            if ex.get('correct_extraction'):
                output += f"**Correct Output:**\n```json\n{json.dumps(ex['correct_extraction'], indent=2)}\n```\n\n"
        
        return output
    
    def _format_warnings(self, warnings: list) -> str:
        """Format warning signs section."""
        output = "## ⚠️ WARNING SIGNS (Common Error Triggers)\n\n"
        output += "When you see these patterns, be extra careful:\n\n"
        
        for w in warnings:
            output += f"- **{w.get('pattern', 'Unknown')}**\n"
            output += f"  - Risk: {w.get('risk', 'N/A')}\n"
            output += f"  - Action: {w.get('action', 'N/A')}\n\n"
        
        return output
    
    def _format_guidelines(self, guidelines: list) -> str:
        """Format new guidelines."""
        output = "## 📋 ADDITIONAL GUIDELINES (From Error Analysis)\n\n"
        
        for i, g in enumerate(guidelines, 1):
            output += f"{i}. {g}\n"
        
        return output
    
    def save_enhanced_prompt(self, enhanced_prompt: str, output_path: str):
        """Save the enhanced prompt."""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(enhanced_prompt)
        print(f"✓ Enhanced prompt saved to: {output_path}")


class MetaLearningPipeline:
    """
    Complete meta-learning pipeline that:
    1. Runs training phase to collect errors
    2. Analyzes errors to generate insights
    3. Enhances prompts for test phase
    """
    
    def __init__(
        self,
        bedrock_client,
        base_prompt_path: str = "prompts/structure_extraction.txt",
        output_dir: str = "semeval_results/meta_learning",
        max_few_shots: int = 5,
        max_errors_to_analyze: int = 20,
        verbose: bool = True
    ):
        self.client = bedrock_client
        self.base_prompt_path = base_prompt_path
        self.output_dir = output_dir
        self.max_few_shots = max_few_shots
        self.max_errors_to_analyze = max_errors_to_analyze
        self.verbose = verbose
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialize logger
        self.logger = MetaLearningLogger(output_dir)
        
        # Initialize components
        self.error_analyzer = ErrorAnalyzer(bedrock_client)
        self.prompt_enhancer = None  # Created after base prompt is confirmed
        
        # Storage
        self.error_log = None
        self.error_analysis = None
        self.enhanced_prompt = None
    
    def collect_errors_from_results(self, results: List[dict]) -> dict:
        """
        Collect errors from pipeline results.
        
        Args:
            results: List of result dicts from NeuroSymbolicPipeline.run()
            
        Returns:
            Error log dict
        """
        errors = []
        
        for r in results:
            # Skip if no ground truth
            if not r.get("ground_truth"):
                continue
            
            # Check for mismatch
            if r.get("prediction") != r.get("ground_truth"):
                error_type = self._classify_error(r)
                
                error_entry = {
                    "id": r.get("id"),
                    "type": error_type,
                    "syllogism": r.get("text"),
                    "ground_truth": r.get("ground_truth"),
                    "prediction": r.get("prediction"),
                    "extracted_structure": r.get("structure"),
                    "self_consistency": r.get("self_consistency"),
                    "plausibility": r.get("plausibility"),
                    "method": r.get("method"),
                    "validity_details": r.get("validity_details")
                }
                
                errors.append(error_entry)
                self.logger.log_error(error_entry)
        
        # Build error log
        error_log = {
            "errors": errors,
            "summary": {
                "total_errors": len(errors),
                "false_valid": sum(1 for e in errors if e["type"] == "FALSE_VALID"),
                "false_invalid": sum(1 for e in errors if e["type"] == "FALSE_INVALID"),
                "extraction_errors": sum(1 for e in errors if e["type"] == "EXTRACTION_ERROR")
            },
            "timestamp": datetime.now().isoformat()
        }
        
        self.error_log = error_log
        return error_log
    
    def _classify_error(self, result: dict) -> str:
        """Classify error type."""
        if result.get("prediction") is None:
            return "EXTRACTION_ERROR"
        elif result.get("prediction") == "VALID" and result.get("ground_truth") == "INVALID":
            return "FALSE_VALID"
        elif result.get("prediction") == "INVALID" and result.get("ground_truth") == "VALID":
            return "FALSE_INVALID"
        return "UNKNOWN"
    
    def save_error_log(self, output_path: str = None):
        """Save error log to file."""
        if output_path is None:
            output_path = os.path.join(self.output_dir, "error_log.json")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.error_log, f, indent=2)
        
        self.logger.info(f"✓ Error log saved to: {output_path}")
        return output_path
    
    def run_analysis_phase(self) -> dict:
        """
        Run error analysis phase.
        
        Returns:
            Error analysis dict
        """
        self.logger.start_phase("ERROR ANALYSIS")
        
        if not self.error_log or self.error_log["summary"]["total_errors"] == 0:
            self.logger.info("No errors to analyze - using base prompt")
            self.logger.end_phase({"status": "skipped", "reason": "no errors"})
            return None
        
        self.logger.info(f"Analyzing {self.error_log['summary']['total_errors']} errors...")
        
        # Run analysis
        self.error_analysis = self.error_analyzer.analyze(
            self.error_log,
            max_errors=self.max_errors_to_analyze
        )
        
        # Log results
        self.logger.log_analysis_result(self.error_analysis)
        
        # Save analysis
        analysis_path = os.path.join(self.output_dir, "error_analysis.json")
        with open(analysis_path, 'w', encoding='utf-8') as f:
            json.dump(self.error_analysis, f, indent=2)
        self.logger.info(f"✓ Error analysis saved to: {analysis_path}")
        
        self.logger.end_phase({
            "patterns_found": len(self.error_analysis.get("error_patterns", [])),
            "few_shots_generated": len(self.error_analysis.get("few_shot_examples", [])),
            "warnings_identified": len(self.error_analysis.get("warning_signs", [])),
            "guidelines_added": len(self.error_analysis.get("new_guidelines", []))
        })
        
        return self.error_analysis
    
    def run_enhancement_phase(self) -> str:
        """
        Generate enhanced prompt from error analysis.
        
        Returns:
            Enhanced prompt string
        """
        self.logger.start_phase("PROMPT ENHANCEMENT")
        
        if not self.error_analysis:
            self.logger.info("No error analysis available - using base prompt")
            with open(self.base_prompt_path, 'r', encoding='utf-8') as f:
                self.enhanced_prompt = f.read()
            self.logger.end_phase({"status": "skipped", "reason": "no analysis"})
            return self.enhanced_prompt
        
        # Initialize enhancer
        self.prompt_enhancer = PromptEnhancer(self.base_prompt_path)
        
        # Get original length
        original_length = len(self.prompt_enhancer.base_prompt)
        
        # Generate enhanced prompt
        self.enhanced_prompt = self.prompt_enhancer.enhance(
            self.error_analysis,
            max_few_shots=self.max_few_shots
        )
        
        # Log enhancement
        self.logger.log_prompt_enhancement(original_length, len(self.enhanced_prompt))
        
        # Save enhanced prompt to file
        enhanced_path = os.path.join(self.output_dir, "enhanced_structure_extraction.txt")
        self.prompt_enhancer.save_enhanced_prompt(self.enhanced_prompt, enhanced_path)
        
        # Also save a copy of the enhanced prompt in the log directory for reference
        enhanced_log_path = os.path.join(self.output_dir, "enhanced_prompt_log.txt")
        self._save_enhanced_prompt_log(enhanced_log_path)
        
        self.logger.end_phase({
            "original_length": original_length,
            "enhanced_length": len(self.enhanced_prompt),
            "added_chars": len(self.enhanced_prompt) - original_length,
            "prompt_file": enhanced_path
        })
        
        return self.enhanced_prompt
    
    def _save_enhanced_prompt_log(self, log_path: str):
        """Save enhanced prompt with metadata to log file."""
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("ENHANCED PROMPT FOR TEST PHASE\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")
            
            # Summary of what was added
            f.write("ENHANCEMENTS ADDED:\n")
            f.write("-" * 40 + "\n")
            if self.error_analysis:
                few_shots = self.error_analysis.get("few_shot_examples", [])
                warnings = self.error_analysis.get("warning_signs", [])
                guidelines = self.error_analysis.get("new_guidelines", [])
                
                f.write(f"  Few-shot examples: {len(few_shots[:self.max_few_shots])}\n")
                f.write(f"  Warning signs: {len(warnings)}\n")
                f.write(f"  New guidelines: {len(guidelines)}\n")
            f.write("\n")
            
            f.write("=" * 80 + "\n")
            f.write("FULL ENHANCED PROMPT:\n")
            f.write("=" * 80 + "\n\n")
            
            f.write(self.enhanced_prompt)
            
            f.write("\n\n" + "=" * 80 + "\n")
            f.write("END OF ENHANCED PROMPT\n")
            f.write("=" * 80 + "\n")
        
        self.logger.info(f"✓ Enhanced prompt log saved to: {log_path}")
        
        # Also log to the main debug log
        self.logger.log_enhanced_prompt_content(self.enhanced_prompt, self.error_analysis)
    
    def get_enhanced_prompt_path(self) -> str:
        """Get path to enhanced prompt file."""
        return os.path.join(self.output_dir, "enhanced_structure_extraction.txt")
    
    def generate_final_report(self):
        """Generate final meta-learning report."""
        return self.logger.save_final_report()
