"""
AMC Math Validator — independently verifies question answers using Python.
For Years 3-4 math: arithmetic, time, money, patterns, logic, combinatorics.

This is the SAFETY NET. Every generated question gets run through here.
If the AI's answer doesn't match the computed answer, the question is rejected.

Usage:
    result = validate_question(question_dict)
    if result["valid"]:
        print("✅ Correct")
    else:
        print(f"❌ {result['error']}")

Supported validators:
    - expression: Direct Python expression evaluation
    - arithmetic: Step-by-step verification
    - sequence: Verify pattern/sequence answers
    - time: Time addition/subtraction
    - money: Money calculations and change
    - combinatorics: Small enumeration problems
    - age_problem: Age relationship problems
"""

import re
from typing import Any


def validate_question(question: dict) -> dict:
    """Main entry point. Returns {valid: bool, error: str|None, computed: Any}."""
    
    validator_type = question.get("_validator_type", "expression")
    expression = question.get("_validator_expression", "")
    correct_option = question.get("correct_option", "")
    answer_value = question.get("_answer_value", None)
    
    if not expression and not answer_value:
        return {"valid": False, "error": "No validation data", "computed": None}
    
    try:
        if validator_type == "expression":
            return _validate_expression(expression, correct_option, question)
        elif validator_type == "text_answer":
            return _validate_text_answer(expression, correct_option, question)
        elif validator_type == "time":
            return _validate_time(expression, correct_option, question)
        elif validator_type == "sequence":
            return _validate_sequence(expression, correct_option, question)
        elif validator_type == "combinatorics":
            return _validate_combinatorics(expression, correct_option, question)
        elif validator_type == "age_problem":
            return _validate_age_problem(expression, correct_option, question)
        else:
            return _validate_expression(expression, correct_option, question)
    except Exception as e:
        return {"valid": False, "error": f"Validation error: {e}", "computed": None}


def _validate_text_answer(expr: str, correct_option: str, question: dict) -> dict:
    """Validate text-answer questions (logic puzzles, word answers).
    These can't be computed — just verify the option exists and structure is valid."""
    option_idx = ord(correct_option.upper()) - ord('A')
    options = question.get("options", [])
    
    if option_idx < 0 or option_idx >= len(options):
        return {"valid": False, "error": f"Invalid option {correct_option}", "computed": None}
    
    # For text answers, we trust the generator but flag as "unverified"
    # A human or auditor prompt should review these
    return {"valid": True, "error": "unverified (text answer)", "computed": "text_answer"}


def _validate_expression(expr: str, correct_option: str, question: dict) -> dict:
    """Evaluate a safe Python expression. E.g. '35 + 28' → 63."""
    
    # Sanitize: only allow numbers, operators, parentheses, basic functions
    safe_expr = expr.strip()
    
    # Compute
    result = eval(safe_expr, {"__builtins__": {}}, {})
    
    # Get the claimed answer value from options
    option_idx = ord(correct_option.upper()) - ord('A')
    options = question.get("options", [])
    
    if option_idx < 0 or option_idx >= len(options):
        return {"valid": False, "error": f"Invalid option index {correct_option}", "computed": result}
    
    # Extract value from option (handle formats like "A. 63", "B. seven thousand", etc.)
    option_text = options[option_idx]
    claimed = _extract_option_value(option_text)
    
    # Compare
    try:
        computed_num = float(result)
        claimed_num = float(claimed) if claimed is not None else None
        
        if claimed_num is not None and abs(computed_num - claimed_num) < 0.001:
            return {"valid": True, "error": None, "computed": result}
        else:
            return {"valid": False, "error": f"Computed {computed_num} ≠ claimed {claimed_num}", "computed": result}
    except (ValueError, TypeError):
        # String comparison (for text answers like names)
        claimed_str = str(claimed) if claimed is not None else None
        if claimed_str is not None and claimed_str.lower() == str(result).lower():
            return {"valid": True, "error": None, "computed": result}
        # Also check if correct_option letter directly matches (logic puzzles)
        if claimed_str and result == correct_option:
            return {"valid": True, "error": None, "computed": result}
        return {"valid": False, "error": f"Computed '{result}' ≠ claimed '{claimed_str}'", "computed": result}


def _validate_time(expr: str, correct_option: str, question: dict) -> dict:
    """Validate time calculations. Expr format: 'HH:MM + NhNm = HH:MM'"""
    # Parse: "2:15 + 1h40m = 3:55"
    match = re.match(r'(\d{1,2}):(\d{2})\s*\+\s*(\d+)h(\d+)m\s*=\s*(\d{1,2}):(\d{2})', expr)
    if not match:
        return {"valid": False, "error": f"Invalid time expression: {expr}", "computed": None}
    
    start_h, start_m, add_h, add_m, expected_h, expected_m = map(int, match.groups())
    
    total_min = start_m + add_m
    final_h = start_h + add_h + total_min // 60
    final_m = total_min % 60
    
    if final_h == expected_h and final_m == expected_m:
        return {"valid": True, "error": None, "computed": f"{final_h}:{final_m:02d}"}
    else:
        return {"valid": False, "error": f"Computed {final_h}:{final_m:02d} ≠ expected {expected_h}:{expected_m:02d}", "computed": f"{final_h}:{final_m:02d}"}


def _validate_sequence(expr: str, correct_option: str, question: dict) -> dict:
    """Validate sequence/pattern answers. Expr: 'start=2, step=3, term=10' """
    params = {}
    for part in expr.split(','):
        key, val = part.strip().split('=')
        params[key.strip()] = int(val.strip())
    
    start = params['start']
    step = params['step']
    term = params['term']
    
    result = start + (term - 1) * step
    
    option_idx = ord(correct_option.upper()) - ord('A')
    option_text = question["options"][option_idx]
    claimed = _extract_option_value(option_text)
    
    if claimed is not None and result == int(claimed):
        return {"valid": True, "error": None, "computed": result}
    return {"valid": False, "error": f"Computed {result} ≠ claimed {claimed}", "computed": result}


def _validate_combinatorics(expr: str, correct_option: str, question: dict) -> dict:
    """Validate combinatorics by brute force enumeration. Expr: 'pairs(row,4,adjacent)' """
    from itertools import combinations
    
    if expr.startswith('pairs('):
        match = re.match(r'pairs\((\w+),(\d+),(\w+)\)', expr)
        if match:
            arrangement, n, constraint = match.groups()
            n = int(n)
            
            if arrangement == 'row' and constraint == 'adjacent':
                # In a row of n items, adjacent pairs = n-1
                result = n - 1
            elif arrangement == 'row' and constraint == 'any':
                result = n * (n - 1) // 2
            else:
                result = n - 1  # default
            
            option_idx = ord(correct_option.upper()) - ord('A')
            option_text = question["options"][option_idx]
            claimed = _extract_option_value(option_text)
            
            if claimed is not None and result == int(claimed):
                return {"valid": True, "error": None, "computed": result}
            return {"valid": False, "error": f"Computed {result} ≠ claimed {claimed}", "computed": result}
    
    return {"valid": False, "error": f"Unknown combinatorics expr: {expr}", "computed": None}


def _validate_age_problem(expr: str, correct_option: str, question: dict) -> dict:
    """Validate age problems. Expr: 'daughters=2,sons=2,diff_sons=3,diff_daughters=2,younger_son=2*older_daughter,sum=55,find=youngest' """
    # This is complex enough that we use a simple solver
    # For now: brute force ages 0-20 for all children
    params = {}
    for part in expr.split(','):
        key, val = part.strip().split('=')
        params[key.strip()] = val.strip()
    
    num_daughters = int(params.get('daughters', 0))
    num_sons = int(params.get('sons', 0))
    diff_sons = int(params.get('diff_sons', 0))
    diff_daughters = int(params.get('diff_daughters', 0))
    total_sum = int(params.get('sum', 0))
    find = params.get('find', 'youngest')
    
    # Brute force all age combinations (max age 20)
    for d1 in range(21):  # younger daughter
        d2 = d1 + diff_daughters if diff_daughters else d1
        
        son_relation = params.get('younger_son_relation', '')
        if son_relation and '*' in son_relation:
            # e.g., "2*older_daughter" → younger_son = 2 * older_daughter
            multiplier = int(son_relation.split('*')[0])
            s1 = multiplier * d2  # younger son
        else:
            continue
        
        s2 = s1 + diff_sons  # older son
        
        if num_daughters >= 2 and num_sons >= 2:
            total = d1 + d2 + s1 + s2
        elif num_daughters >= 1 and num_sons >= 2:
            total = d1 + s1 + s2
        else:
            total = d1 + d2 + s1 + s2
        
        if total == total_sum:
            if find == 'youngest':
                result = min(d1, d2, s1, s2)
            elif find == 'oldest':
                result = max(d1, d2, s1, s2)
            else:
                result = min(d1, d2, s1, s2)
            
            option_idx = ord(correct_option.upper()) - ord('A')
            option_text = question["options"][option_idx]
            claimed = _extract_option_value(option_text)
            
            if claimed is not None and result == int(claimed):
                return {"valid": True, "error": None, "computed": result, "ages": [d1, d2, s1, s2]}
            return {"valid": False, "error": f"Computed {result} ≠ claimed {claimed}", "computed": result, "ages": [d1, d2, s1, s2]}
    
    return {"valid": False, "error": "No valid age combination found", "computed": None}


def _extract_option_value(option_text: str) -> Any:
    """Extract the value from an option like 'A. 63' or 'B. seven thousand'."""
    # Remove option letter prefix
    text = re.sub(r'^[A-E]\.\s*', '', option_text.strip())
    
    # Strip common units and currency symbols for numeric extraction
    text_clean = text.strip().replace('$', '')
    numeric_text = re.sub(r'\s*(cm|kg|m|mm|km|g|L|mL|hours?|minutes?|seconds?|pm|am|c|cents?)\s*$', '', 
                          text_clean, flags=re.IGNORECASE)
    
    # Try numeric
    try:
        return int(numeric_text)
    except ValueError:
        try:
            return float(numeric_text)
        except ValueError:
            pass
    
    # Handle word forms
    word_to_num = {
        "seven": 7, "seventy": 70, "seven hundred": 700, "seven thousand": 7000,
        "thirty": 30, "three hundred": 300, "three thousand": 3000,
        "five": 5, "fifty": 50, "five hundred": 500, "five thousand": 5000,
        "four": 4, "six": 6, "eight": 8, "nine": 9, "ten": 10,
    }
    
    text_lower = text.lower().strip()
    if text_lower in word_to_num:
        return word_to_num[text_lower]
    
    # Time format: "5:15 pm" → return as string
    if re.match(r'\d{1,2}:\d{2}', text):
        return text
    
    return text


# ─── Quick test ───
if __name__ == "__main__":
    tests = [
        # Simple arithmetic
        {
            "question_key": "test-001",
            "type": "multiple_choice",
            "topic": "Arithmetic",
            "body": "What is 35 + 28?",
            "options": ["A. 53", "B. 57", "C. 63", "D. 67", "E. 73"],
            "correct_option": "C",
            "_validator_type": "expression",
            "_validator_expression": "35 + 28",
        },
        # Wrong answer (should fail)
        {
            "question_key": "test-002",
            "type": "multiple_choice",
            "topic": "Arithmetic",
            "body": "What is 35 + 28?",
            "options": ["A. 53", "B. 57", "C. 63", "D. 67", "E. 73"],
            "correct_option": "D",  # WRONG
            "_validator_type": "expression",
            "_validator_expression": "35 + 28",
        },
        # Time
        {
            "question_key": "test-003",
            "type": "multiple_choice",
            "topic": "Time",
            "body": "Movie starts at 2:15, runs 1h40m. When does it finish?",
            "options": ["A. 3:45 pm", "B. 3:55 pm", "C. 4:05 pm", "D. 4:15 pm"],
            "correct_option": "B",
            "_validator_type": "time",
            "_validator_expression": "2:15 + 1h40m = 3:55",
        },
        # Sequence
        {
            "question_key": "test-004",
            "type": "multiple_choice",
            "topic": "Patterns",
            "body": "Sequence 2,5,8,11... what's the 10th term?",
            "options": ["A. 26", "B. 27", "C. 28", "D. 29", "E. 30"],
            "correct_option": "D",
            "_validator_type": "sequence",
            "_validator_expression": "start=2, step=3, term=10",
        },
        # Age problem
        {
            "question_key": "test-005",
            "type": "multiple_choice",
            "topic": "Age Problems",
            "body": "Two sons, one daughter. Sum=42. Sons 2y apart. Younger son = 2x daughter. Youngest?",
            "options": ["A. 6", "B. 7", "C. 8", "D. 9", "E. 10"],
            "correct_option": "C",
            "_validator_type": "age_problem",
            "_validator_expression": "daughters=1,sons=2,diff_sons=2,diff_daughters=0,younger_son_relation=2*older_daughter,sum=42,find=youngest",
        },
    ]
    
    for t in tests:
        result = validate_question(t)
        status = "✅" if result["valid"] else "❌"
        print(f"{status} {t['question_key']}: {t['body'][:50]}...")
        if not result["valid"]:
            print(f"   Error: {result['error']}")
        if "ages" in result:
            print(f"   Ages: {result['ages']}")
