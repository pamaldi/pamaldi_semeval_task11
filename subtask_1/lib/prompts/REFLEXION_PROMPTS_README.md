# Reflexion Prompts Documentation

## Overview

The Reflexion module uses external text files for all prompts to make them easy to customize and maintain. All prompts are stored in the `prompts/` directory.

## Prompt Files

### 1. `reflexion_base.txt`
**Purpose**: Main template for reflection prompts

**Variables**:
- `{syllogism}` - The syllogism text
- `{code}` - The previous code that failed
- `{stderr}` - Error output from execution
- `{failure_guidance}` - Specific guidance based on failure type
- `{attempt_history}` - History of previous attempts (if any)

**Usage**: This is the base template that combines all other prompts.

---

### 2. `reflexion_syntax_error.txt`
**Purpose**: Guidance for fixing syntax errors

**When used**: When code has Python syntax errors (missing colons, indentation, brackets, etc.)

**Customization**: Edit this file to add more syntax error tips specific to your use case.

---

### 3. `reflexion_runtime_error.txt`
**Purpose**: Guidance for fixing runtime errors

**When used**: When code runs but crashes (NameError, AttributeError, etc.)

**Customization**: Add domain-specific runtime error tips (e.g., pyDatalog predicate issues).

---

### 4. `reflexion_wrong_prediction.txt`
**Purpose**: Guidance for fixing incorrect predictions

**When used**: When code runs successfully but produces wrong answer (only with ground truth)

**Customization**: Add logic-specific tips for your domain (e.g., syllogism reasoning rules).

---

### 5. `reflexion_no_code.txt`
**Purpose**: Guidance when no code is extracted

**When used**: When the model's response doesn't contain valid code blocks

**Customization**: Adjust code block requirements for your format.

---

### 6. `reflexion_timeout.txt`
**Purpose**: Guidance for fixing timeout issues

**When used**: When code takes too long to execute (>5 seconds)

**Customization**: Add tips specific to your execution environment.

---

### 7. `reflexion_unknown.txt`
**Purpose**: Generic guidance for unknown errors

**When used**: When error type cannot be classified

**Customization**: Add general debugging checklist items.

---

### 8. `reflexion_attempt_history.txt`
**Purpose**: Template for showing previous attempt history

**Variables**:
- `{current_attempt}` - Current attempt number
- `{max_attempts}` - Maximum attempts allowed
- `{attempt_list}` - List of previous attempts and their failure types

**Usage**: Inserted into base template when there are multiple attempts.

---

### 9. `reflexion_generate_reflection.txt` (NEW - True Reflexion)
**Purpose**: Template for asking LLM to generate its own reflection on failure

**Variables**:
- `{syllogism}` - The syllogism being solved
- `{code}` - The code that failed
- `{failure_type}` - Type of failure (syntax_error, runtime_error, etc.)
- `{stderr}` - Error message
- `{attempt_number}` - Which attempt this was

**Usage**: Called after each failed attempt to generate LLM reflection.

**Key Feature**: Uses lower temperature (0.3) for analytical task.

---

### 10. `reflexion_with_memory.txt` (NEW - True Reflexion)
**Purpose**: Template for retry prompts that include accumulated reflections

**Variables**:
- `{memory_section}` - All accumulated reflections from previous attempts
- `{syllogism}` - The syllogism being solved
- `{failure_type}` - Type of failure
- `{stderr}` - Error message
- `{code}` - Previous code
- `{failure_guidance}` - Failure-specific guidance

**Usage**: Builds the prompt for retry attempts with full memory context.

**Key Feature**: Includes ALL past reflections as "lessons learned".

---

## How It Works

### Loading Process

1. When `ReflexionExecutor` is initialized, it calls `_load_prompts()`
2. All prompt files are loaded from `prompts/` directory
3. Prompts are stored in `self.reflexion_prompts` dictionary
4. If a file is missing, a warning is shown and placeholder is used

### Building Reflection Prompts

1. `build_reflection_prompt()` is called when code fails
2. Selects appropriate failure guidance based on `FailureType`
3. Builds attempt history if multiple attempts exist
4. Fills in template variables using `.format()`
5. Returns complete reflection prompt

### Example Flow

```python
# 1. Code fails with syntax error
failure_type = FailureType.SYNTAX_ERROR

# 2. Load syntax error guidance
guidance = self.reflexion_prompts['syntax_error']

# 3. Build attempt history (if needed)
if len(attempts) > 1:
    history = self.reflexion_prompts['attempt_history'].format(...)
else:
    history = ""

# 4. Fill in base template
reflection = self.reflexion_prompts['base'].format(
    syllogism=syllogism,
    code=previous_code,
    stderr=error_message,
    failure_guidance=guidance,
    attempt_history=history
)

# 5. Send to model for regeneration
new_code = regenerate_code(reflection)
```

---

## Customization Guide

### Adding New Failure Types

1. Create new prompt file: `prompts/reflexion_new_type.txt`
2. Add to `_load_prompts()` in reflexion module:
   ```python
   'new_type': 'reflexion_new_type.txt'
   ```
3. Add to `FailureType` enum:
   ```python
   NEW_TYPE = "new_type"
   ```
4. Add to failure guidance map in `build_reflection_prompt()`:
   ```python
   FailureType.NEW_TYPE: self.reflexion_prompts['new_type']
   ```

### Modifying Existing Prompts

Simply edit the text files in `prompts/` directory. Changes take effect on next run.

**Example**: To add more syntax error tips:
```bash
# Edit prompts/reflexion_syntax_error.txt
# Add your tips to the list
# Save and run - new tips will be used
```

### Testing Prompts

1. Edit prompt file
2. Run quick test:
   ```bash
   python test_reflexion_quick.py
   ```
3. Check logs to see if new prompts are used:
   ```bash
   cat semeval_results/reflexion_*/logs/*.txt
   ```

---

## Prompt Variables Reference

### Available in `reflexion_base.txt`:
- `{syllogism}` - The input syllogism
- `{code}` - Previous code that failed
- `{stderr}` - Error message from execution
- `{failure_guidance}` - Failure-specific guidance (from other files)
- `{attempt_history}` - Previous attempts (from attempt_history.txt)

### Available in `reflexion_attempt_history.txt`:
- `{current_attempt}` - Current attempt number (e.g., 2)
- `{max_attempts}` - Maximum attempts (e.g., 3)
- `{attempt_list}` - Formatted list of previous attempts

---

## Best Practices

### 1. Keep Prompts Focused
Each failure type prompt should focus on that specific issue. Don't mix guidance.

### 2. Use Clear Formatting
Use markdown formatting (headers, lists, code blocks) for readability.

### 3. Provide Examples
Include concrete examples of fixes when possible.

### 4. Test Changes
Always test prompt changes with `test_reflexion_quick.py` before full runs.

### 5. Version Control
Keep prompt files in version control to track changes over time.

### 6. Document Custom Prompts
If you create custom prompts, document them in this file.

---

## Troubleshooting

### Prompt Not Loading
**Symptom**: Warning message "Prompt file not found"
**Solution**: Check file exists in `prompts/` directory with correct name

### Variables Not Replaced
**Symptom**: Prompt contains `{variable}` in output
**Solution**: Check variable name matches exactly in `.format()` call

### Prompt Not Used
**Symptom**: Old prompt text appears in logs
**Solution**: Restart Python session to reload prompt files

### Encoding Issues
**Symptom**: Special characters appear garbled
**Solution**: Ensure files are saved as UTF-8 encoding

---

## File Locations

```
prompts/
├── reflexion_base.txt              # Main template
├── reflexion_syntax_error.txt      # Syntax error guidance
├── reflexion_runtime_error.txt     # Runtime error guidance
├── reflexion_wrong_prediction.txt  # Wrong prediction guidance
├── reflexion_no_code.txt           # No code extracted guidance
├── reflexion_timeout.txt           # Timeout guidance
├── reflexion_unknown.txt           # Unknown error guidance
├── reflexion_attempt_history.txt   # Attempt history template
└── REFLEXION_PROMPTS_README.md     # This file
```

---

## Example: Customizing for Different Domains

### For SQL Generation:
Edit `reflexion_syntax_error.txt`:
```
**SYNTAX ERROR**: Your SQL has syntax errors.

Common fixes:
- Check all SQL keywords are uppercase
- Verify table and column names exist
- Ensure proper JOIN syntax
- Check for missing semicolons
```

### For Math Problems:
Edit `reflexion_wrong_prediction.txt`:
```
**WRONG ANSWER**: Your calculation is incorrect.

Common fixes:
- Check order of operations
- Verify variable values
- Review formula application
- Check for rounding errors
```

---

## Version History

- **v1.0** (2026-01-28): Initial external prompt system
  - Moved all prompts to external files
  - Added template system with variables
  - Created documentation

---

## Future Enhancements

Potential improvements:
- [ ] Multi-language prompt support
- [ ] Prompt versioning system
- [ ] A/B testing different prompts
- [ ] Automatic prompt optimization
- [ ] Domain-specific prompt libraries

---

## Support

For questions or issues with prompts:
1. Check this documentation
2. Review example prompts in `prompts/` directory
3. Test with `test_reflexion_quick.py`
4. Check logs in `semeval_results/reflexion_*/logs/`
