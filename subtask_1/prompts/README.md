# Prompts Directory

This directory contains all system prompts used by the SemEval 2026 Task 11 pipeline for syllogistic reasoning.

## Prompt Files

### 1. `pydatalog_detailed.txt` (Default)
**Purpose**: Comprehensive pyDatalog conversion prompt with extensive rules and examples.

**Features**:
- Detailed encoding rules for all proposition types (A, E, I, O)
- 10 complete examples covering valid and invalid syllogisms
- Pre-output checklist for verification
- Extensive guidance on rule direction and predicate definitions

**Use Case**: Best for complex syllogisms requiring careful logical encoding.

**Usage**:
```python
prompt_builder = PromptBuilder()
prompt_builder.use_detailed_prompt()  # This is the default
```

---

### 2. `pydatalog_simple.txt`
**Purpose**: Simplified pyDatalog conversion prompt with concise rules.

**Features**:
- Condensed rule set in table format
- 10 examples with minimal explanation
- Faster to process for the LLM
- Focus on pattern matching

**Use Case**: When you need faster inference or the LLM is already familiar with the task.

**Usage**:
```python
prompt_builder = PromptBuilder()
prompt_builder.use_simple_prompt()
```

---

### 3. `prolog.txt`
**Purpose**: SWI-Prolog conversion prompt for native Prolog execution.

**Features**:
- SWI-Prolog specific syntax
- Uses `valid_syllogism` predicate for checking
- Handles negation with `\+` operator
- 7 detailed examples with analysis

**Use Case**: When using PrologExecutor with pyswip for execution.

**Usage**:
```python
prompt_builder = PromptBuilder()
prompt_builder.use_prolog_prompt()
```

---

### 4. `chain_of_thought.txt`
**Purpose**: Chain-of-Thought reasoning prompt for direct LLM analysis.

**Features**:
- 5-step structured analysis format
- 12 diverse examples (valid/invalid, plausible/implausible)
- No code generation - pure logical reasoning
- Extracts VALID/INVALID from Step 5

**Use Case**: When using CotExecutor to extract predictions directly from LLM reasoning.

**Usage**:
```python
prompt_builder = PromptBuilder()
prompt_builder.use_cot_prompt()
```

---

## Prompt Selection Guide

| Executor | Recommended Prompt | Alternative |
|----------|-------------------|-------------|
| `PyDatalogExecutor` | `pydatalog_detailed.txt` | `pydatalog_simple.txt` |
| `PrologExecutor` | `prolog.txt` | - |
| `CotExecutor` | `chain_of_thought.txt` | - |

## Customization

To create a custom prompt:

1. Create a new `.txt` file in this directory
2. Write your prompt following the format of existing prompts
3. Load it in your code:
```python
prompt_builder = PromptBuilder()
prompt_builder.system_prompt = prompt_builder._load_prompt("your_custom_prompt.txt")
```

## Prompt Engineering Tips

1. **Be Explicit**: Clearly state what output format you expect
2. **Use Examples**: Few-shot examples dramatically improve accuracy
3. **Add Constraints**: Specify what NOT to do (e.g., "NO explanations")
4. **Test Iteratively**: Start with simple cases, then add complexity
5. **Version Control**: Keep track of prompt versions and their performance

## Performance Notes

Based on testing with Qwen2.5-3B-Instruct:

- **pydatalog_detailed.txt**: ~75-80% accuracy on training set
- **pydatalog_simple.txt**: ~70-75% accuracy (faster inference)
- **prolog.txt**: ~70-75% accuracy (depends on pyswip setup)
- **chain_of_thought.txt**: ~65-70% accuracy (no code execution errors)

Your results may vary based on model size and quantization settings.
