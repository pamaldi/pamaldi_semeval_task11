# Prompts Quick Reference

## Available Prompts

| Prompt File | Size | Executor | Best For |
|-------------|------|----------|----------|
| `pydatalog_detailed.txt` | 8.5 KB | PyDatalogExecutor | Complex syllogisms, high accuracy |
| `pydatalog_simple.txt` | 5.2 KB | PyDatalogExecutor | Fast inference, simple cases |
| `prolog.txt` | 6.7 KB | PrologExecutor | Native Prolog execution |
| `chain_of_thought.txt` | 8.5 KB | CotExecutor | Direct reasoning, no code |

## Quick Usage

```python
from semeval_pipeline_classes import PromptBuilder

# Default (detailed pyDatalog)
pb = PromptBuilder()

# Switch prompts
pb.use_simple_prompt()      # Faster pyDatalog
pb.use_prolog_prompt()      # Prolog
pb.use_cot_prompt()         # Chain-of-Thought
pb.use_detailed_prompt()    # Back to default
```

## Prompt Characteristics

### pydatalog_detailed.txt (DEFAULT)
- ✅ Most comprehensive rules
- ✅ 10 detailed examples
- ✅ Pre-output checklist
- ✅ Best accuracy (~75-80%)
- ⚠️ Slower inference

### pydatalog_simple.txt
- ✅ Concise rules
- ✅ 10 examples
- ✅ Faster inference
- ⚠️ Slightly lower accuracy (~70-75%)

### prolog.txt
- ✅ Native Prolog syntax
- ✅ 7 examples with analysis
- ✅ Works with pyswip
- ⚠️ Requires SWI-Prolog installed

### chain_of_thought.txt
- ✅ No code execution
- ✅ 12 diverse examples
- ✅ 5-step structured analysis
- ⚠️ Lower accuracy (~65-70%)
- ✅ No syntax errors

## When to Use Each

| Scenario | Recommended Prompt |
|----------|-------------------|
| Production pipeline | `pydatalog_detailed.txt` |
| Quick experiments | `pydatalog_simple.txt` |
| Using pyswip | `prolog.txt` |
| No code execution | `chain_of_thought.txt` |
| Debugging LLM reasoning | `chain_of_thought.txt` |
| Maximum accuracy | `pydatalog_detailed.txt` |
| Fastest inference | `pydatalog_simple.txt` |

## Customization

To create a custom prompt:

1. Copy an existing prompt file
2. Modify the rules/examples
3. Save as `prompts/my_prompt.txt`
4. Load it:
```python
pb = PromptBuilder()
pb.system_prompt = pb._load_prompt("my_prompt.txt")
```

## Performance Tips

1. **Start with detailed**: Use `pydatalog_detailed.txt` as baseline
2. **Test on subset**: Validate on 20-50 examples first
3. **Compare metrics**: Track accuracy, F1, content effect
4. **Iterate**: Adjust examples and rules based on errors
5. **Document changes**: Keep notes on what works

## Common Issues

### FileNotFoundError
```
FileNotFoundError: Prompt file not found: prompts/xxx.txt
```
**Solution**: Ensure `prompts/` directory exists with all `.txt` files

### Empty Prompt
```
system_prompt is empty or None
```
**Solution**: Check file encoding is UTF-8, not binary

### Wrong Executor
```
Using prolog.txt with PyDatalogExecutor
```
**Solution**: Match prompt to executor (see table above)

## Testing

Verify all prompts load:
```bash
python test_prompts.py
```

Test a specific prompt:
```python
from semeval_pipeline_classes import PromptBuilder

pb = PromptBuilder()
pb.use_simple_prompt()
print(f"Loaded: {len(pb.system_prompt)} chars")
print(pb.system_prompt[:200])  # Preview
```

## See Also

- **Full Documentation**: `prompts/README.md`
- **Refactoring Details**: `doc/PROMPT_REFACTORING.md`
- **Test Script**: `test_prompts.py`
