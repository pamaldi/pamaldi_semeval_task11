# Prompt Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    SemEval Pipeline                         │
│                                                             │
│  ┌──────────────┐      ┌──────────────┐                   │
│  │   Config     │      │  DataLoader  │                   │
│  └──────────────┘      └──────────────┘                   │
│                                                             │
│  ┌──────────────┐      ┌──────────────┐                   │
│  │ModelManager  │      │PromptBuilder │◄─────────────┐    │
│  └──────────────┘      └──────┬───────┘              │    │
│                               │                       │    │
│  ┌──────────────┐             │ loads                │    │
│  │ Inference    │             ▼                       │    │
│  │   Engine     │      ┌─────────────┐               │    │
│  └──────┬───────┘      │   prompts/  │               │    │
│         │              │             │               │    │
│         │              │  ┌────────┐ │               │    │
│         │              │  │detailed│ │◄──default─────┤    │
│         │              │  └────────┘ │               │    │
│         │              │  ┌────────┐ │               │    │
│         │              │  │ simple │ │◄──optional────┤    │
│         │              │  └────────┘ │               │    │
│         │              │  ┌────────┐ │               │    │
│         │              │  │ prolog │ │◄──optional────┤    │
│         │              │  └────────┘ │               │    │
│         │              │  ┌────────┐ │               │    │
│         │              │  │  cot   │ │◄──optional────┤    │
│         │              │  └────────┘ │               │    │
│         │              └─────────────┘               │    │
│         │                                            │    │
│         ▼                                            │    │
│  ┌──────────────┐                                   │    │
│  │  Executors   │                                   │    │
│  │              │                                   │    │
│  │ ┌──────────┐ │                                   │    │
│  │ │PyDatalog │ │───uses───► pydatalog_detailed ───┘    │
│  │ └──────────┘ │         or pydatalog_simple            │
│  │ ┌──────────┐ │                                        │
│  │ │  Prolog  │ │───uses───► prolog.txt                 │
│  │ └──────────┘ │                                        │
│  │ ┌──────────┐ │                                        │
│  │ │   CoT    │ │───uses───► chain_of_thought.txt       │
│  │ └──────────┘ │                                        │
│  └──────────────┘                                        │
│                                                           │
│  ┌──────────────┐                                        │
│  │  Evaluator   │                                        │
│  └──────────────┘                                        │
└───────────────────────────────────────────────────────────┘
```

## Prompt Flow

```
User Code
   │
   ▼
PromptBuilder.__init__()
   │
   ├─► _load_prompt("pydatalog_detailed.txt")  [DEFAULT]
   │      │
   │      ▼
   │   Read from disk
   │      │
   │      ▼
   │   self.system_prompt = file_content
   │
   ▼
User calls: prompt_builder.use_simple_prompt()
   │
   ├─► _load_prompt("pydatalog_simple.txt")
   │      │
   │      ▼
   │   Read from disk
   │      │
   │      ▼
   │   self.system_prompt = file_content
   │
   ▼
InferenceEngine.run_inference()
   │
   ├─► prompt_builder.build_prompt(syllogism, tokenizer)
   │      │
   │      ├─► Replace {syllogism} placeholder
   │      │
   │      ├─► Create messages array
   │      │      [{"role": "system", "content": system_prompt},
   │      │       {"role": "user", "content": syllogism}]
   │      │
   │      └─► tokenizer.apply_chat_template()
   │             │
   │             ▼
   │          Formatted prompt string
   │
   ▼
Model generates response
   │
   ▼
Executor processes response
```

## Prompt Selection Decision Tree

```
Start
  │
  ▼
Need code execution?
  │
  ├─ No ──► Use chain_of_thought.txt
  │           │
  │           └─► CotExecutor
  │
  └─ Yes ──► Which language?
              │
              ├─ Prolog ──► Use prolog.txt
              │              │
              │              └─► PrologExecutor
              │
              └─ pyDatalog ──► Need max accuracy?
                               │
                               ├─ Yes ──► Use pydatalog_detailed.txt
                               │           │
                               │           └─► PyDatalogExecutor
                               │
                               └─ No ──► Use pydatalog_simple.txt
                                          │
                                          └─► PyDatalogExecutor
```

## File Dependencies

```
semeval_pipeline_classes.py
   │
   ├─► imports os, json, etc.
   │
   └─► class PromptBuilder
          │
          ├─► __init__(prompts_dir="prompts")
          │      │
          │      └─► _load_prompt("pydatalog_detailed.txt")
          │             │
          │             └─► os.path.join(prompts_dir, filename)
          │                    │
          │                    └─► open(filepath, 'r', encoding='utf-8')
          │
          ├─► use_simple_prompt()
          │      └─► _load_prompt("pydatalog_simple.txt")
          │
          ├─► use_prolog_prompt()
          │      └─► _load_prompt("prolog.txt")
          │
          └─► use_cot_prompt()
                 └─► _load_prompt("chain_of_thought.txt")
```

## Prompt File Structure

Each prompt file follows this structure:

```
┌─────────────────────────────────────┐
│ Prompt File (.txt)                  │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ Header / Title                  │ │
│ └─────────────────────────────────┘ │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ Critical Rules                  │ │
│ │ - Rule 1                        │ │
│ │ - Rule 2                        │ │
│ │ - ...                           │ │
│ └─────────────────────────────────┘ │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ Encoding Patterns               │ │
│ │ - A-type: ...                   │ │
│ │ - E-type: ...                   │ │
│ │ - I-type: ...                   │ │
│ │ - O-type: ...                   │ │
│ └─────────────────────────────────┘ │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ Examples (5-12)                 │ │
│ │                                 │ │
│ │ Example 1: [Valid]              │ │
│ │   Input: ...                    │ │
│ │   Output: ...                   │ │
│ │                                 │ │
│ │ Example 2: [Invalid]            │ │
│ │   Input: ...                    │ │
│ │   Output: ...                   │ │
│ │                                 │ │
│ │ ...                             │ │
│ └─────────────────────────────────┘ │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ Output Format                   │ │
│ │ - Template                      │ │
│ │ - Constraints                   │ │
│ └─────────────────────────────────┘ │
└─────────────────────────────────────┘
```

## Execution Pipeline

```
┌─────────────────────────────────────────────────────────┐
│                    Execution Flow                       │
└─────────────────────────────────────────────────────────┘

1. Load Data
   ├─► train_data.json
   └─► test_data.json

2. Load Model
   └─► Qwen2.5-3B-Instruct (or other)

3. Build Prompts
   ├─► PromptBuilder loads prompt file
   ├─► For each syllogism:
   │   ├─► Insert syllogism into prompt template
   │   └─► Apply chat template
   └─► Return formatted prompts

4. Run Inference
   ├─► For each prompt:
   │   ├─► Tokenize
   │   ├─► Generate with model
   │   └─► Decode response
   └─► Return responses

5. Execute Programs
   ├─► PyDatalogExecutor:
   │   ├─► Extract Python code
   │   ├─► Save to .py file
   │   ├─► Execute with subprocess
   │   └─► Parse output (VALID/INVALID)
   │
   ├─► PrologExecutor:
   │   ├─► Extract Prolog code
   │   ├─► Save to .pl file
   │   ├─► Query with pyswip
   │   └─► Return result
   │
   └─► CotExecutor:
       ├─► Parse response text
       ├─► Find "Step 5 - Answer:"
       └─► Extract VALID/INVALID

6. Evaluate
   ├─► Calculate accuracy
   ├─► Calculate content effect
   ├─► Calculate combined metric
   └─► Generate report
```

## Prompt Customization Points

```
PromptBuilder
   │
   ├─► prompts_dir parameter
   │      └─► Change directory location
   │
   ├─► _load_prompt() method
   │      └─► Add preprocessing/validation
   │
   ├─► build_prompt() method
   │      └─► Customize message format
   │
   └─► system_prompt attribute
          └─► Direct assignment for custom prompts
```

## Extension Points

To add a new prompt:

```
1. Create new file
   └─► prompts/my_new_prompt.txt

2. Add loading method (optional)
   └─► def use_my_prompt(self):
           self.system_prompt = self._load_prompt("my_new_prompt.txt")
           return self

3. Use in code
   └─► prompt_builder.use_my_prompt()
```

## See Also

- **Usage Guide**: `prompts/README.md`
- **Quick Reference**: `prompts/QUICK_REFERENCE.md`
- **Refactoring Details**: `doc/PROMPT_REFACTORING.md`
