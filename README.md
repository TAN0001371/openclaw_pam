# Pam's Tools

Tools and pipelines I built to help Stewart. Each tool lives in its own directory.

## AMC Question Generator (`amc/`)

Generates original Australian Mathematics Competition practice questions for Middle Primary (Years 3-4).

### How it works

1. **Gemini generates** AMC-style questions from a topic/config spec
2. **Math validator** independently computes every answer using Python
3. Questions that fail validation are flagged — no wrong answers slip through

### Usage

```bash
# Generate 5 quick practice questions
python3 amc/generate.py --count 5

# Generate on a specific topic
python3 amc/generate.py --topic money --count 5

# Generate a full 30-question paper
python3 amc/generate.py --mode full

# Validate existing questions
python3 amc/math_validator.py
```

### Structure

```
amc/
  config/           # Subject configuration (topics, difficulty, modes)
  prompts/          # Generation prompts (coming)
  output/           # Generated question packs (JSON)
  generate.py       # Main generation pipeline
  math_validator.py # Independent answer verification
  transcribe.py     # Image → text (for reference papers)
```

### Validation

The math validator supports:
- **Arithmetic**: expression evaluation
- **Time**: clock arithmetic
- **Sequences**: pattern/step verification
- **Combinatorics**: brute-force enumeration
- **Age problems**: brute-force solver
- **Text answers**: logic puzzle trust-but-flag

Every generated question must pass validation before it's saved.
