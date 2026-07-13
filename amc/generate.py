#!/usr/bin/env python3
"""
AMC Question Generator — generates original AMC-style questions using Gemini,
then validates every answer independently with the math validator.

Usage:
    python3 generate.py              # Generate a quick practice pack
    python3 generate.py --mode full  # Full 30-question paper
    python3 generate.py --topic money --count 5  # 5 money questions
"""

import json, sys, os, argparse, urllib.request, urllib.parse
from pathlib import Path
from datetime import datetime

# Add parent to path for math_validator import
sys.path.insert(0, str(Path(__file__).parent))
from math_validator import validate_question

ROOT = Path(__file__).parent.parent
CONFIG_DIR = Path(__file__).parent / "config"
KEY_FILE = Path(__file__).parent / ".gemini_key"

MODEL = "gemini-3.1-flash-lite"


def load_config():
    with open(CONFIG_DIR / "amc_middle_primary.json") as f:
        return json.load(f)


def generate_batch(mode: str = "quick", topic: str = None, count: int = None) -> list:
    """Generate a batch of AMC questions using Gemini."""
    
    config = load_config()
    
    if mode == "quick":
        mode_config = config["generation_modes"]["quick_practice"]
        target_count = count or 5
    elif mode == "topic":
        mode_config = config["generation_modes"]["topic_test"]
        target_count = count or 10
    elif mode == "full":
        mode_config = config["generation_modes"]["full_paper"]
        target_count = count or 30
    else:
        mode_config = config["generation_modes"]["quick_practice"]
        target_count = count or 5
    
    topics_str = ""
    if topic:
        topic_info = next((t for t in config["topics"] if t["id"] == topic), None)
        if topic_info:
            topics_str = f"\nOnly generate questions on the topic: {topic_info['name']} ({topic_info['id']})"
    
    prompt = f"""You are an expert mathematics question writer for the Australian Mathematics Competition (AMC) Middle Primary Division (Years 3-4). Create {target_count} original AMC-style questions.

TOPICS AND DIFFICULTY:
{json.dumps(config["topics"], indent=2)}{topics_str}

RULES:
1. All questions must be original — DO NOT copy from any existing paper
2. Every question must have exactly ONE correct answer
3. Multiple choice questions: 5 options (A-E) with only ONE correct
4. Questions 1-10 style: 3-mark difficulty — simple, direct
5. Questions 11-20 style: 4-mark difficulty — slightly more thought required
6. Questions 21-30 style: 5+ mark difficulty — multi-step or trickier
7. Include a "validator" field with the math expression to verify the answer
8. Include a brief explanation suitable for Years 3-4 students

OUTPUT FORMAT (JSON array):
[
  {{
    "question_key": "amc-mp-XXX",
    "type": "multiple_choice",
    "topic": "arithmetic",
    "difficulty": "easy",
    "body": "Question text here",
    "options": ["A. option1", "B. option2", "C. option3", "D. option4", "E. option5"],
    "correct_option": "A",
    "answer_explanation": "Simple explanation a Year 3-4 student can follow",
    "marks": 3,
    "suggested_time_minutes": 1,
    "_validator_type": "expression",
    "_validator_expression": "math expression to verify"
  }}
]

VALIDATOR TYPES AND FORMATS:
- expression: For arithmetic, place value, geometry, measurement: e.g. "35 + 28" or "20 // 3" or "(12*4)+(2*3)"
- time: For time calculations: e.g. "2:15 + 1h40m = 3:55"
- sequence: For number patterns: e.g. "start=2, step=3, term=10"
- combinatorics: For counting/paths: e.g. "pairs(row,4,adjacent)"
- age_problem: For age/multi-person relations: e.g. "daughters=1,sons=2,diff_sons=2,younger_son_relation=2*older_daughter,sum=42,find=youngest"
- text_answer: For logic puzzles with word/name answers. Use expression "none" with this type.

IMPORTANT: Use text_answer type for any question where the answer is a word, name, or non-numeric label. Only use expression/sequence/time/combinatorics/age_problem when the answer is a NUMBER.

Generate EXACTLY {target_count} questions as valid JSON array. No markdown, no commentary — pure JSON.
"""
    
    return _call_gemini(prompt)


def _call_gemini(prompt: str, retries: int = 3) -> list:
    """Call Gemini API to generate questions."""
    
    with open(KEY_FILE) as f:
        key_val = f.read().strip()

    url = "https://generativelanguage.googleapis.com/v1beta/models/" + MODEL + ":generateContent?" + urllib.parse.urlencode({"key": key_val})
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.8,
            "topP": 0.95,
            "maxOutputTokens": 8192,
        }
    }
    
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read())
            
            text = result["candidates"][0]["content"]["parts"][0]["text"]
            
            # Extract JSON from response (handle markdown code blocks)
            text = text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            text = text.strip()
            
            questions = json.loads(text)
            return questions
            
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            print(f"  HTTP {e.code} (attempt {attempt + 1}/{retries})", file=sys.stderr)
            if attempt == retries - 1:
                raise
        except json.JSONDecodeError as e:
            print(f"  JSON parse error (attempt {attempt + 1}/{retries}): {e}", file=sys.stderr)
            if attempt == retries - 1:
                print(f"  Raw text: {text[:500]}", file=sys.stderr)
                raise
    
    return []


def validate_batch(questions: list) -> dict:
    """Run math validator on every question. Returns summary."""
    results = {"total": len(questions), "passed": 0, "failed": 0, "details": []}
    
    for q in questions:
        result = validate_question(q)
        if result["valid"]:
            results["passed"] += 1
            results["details"].append({"key": q["question_key"], "status": "pass"})
        else:
            results["failed"] += 1
            results["details"].append({
                "key": q["question_key"],
                "status": "fail",
                "error": result["error"],
                "computed": result.get("computed"),
                "ages": result.get("ages"),
            })
    
    return results


def save_pack(questions: list, mode: str, output_dir: Path = None):
    """Save generated questions as a content pack."""
    if output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        output_dir = Path(__file__).parent / "output" / timestamp
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    pack = {
        "schema_version": "1.1",
        "pack_id": f"amc-mp-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "pack_name": f"AMC Middle Primary — {mode.replace('_', ' ').title()}",
        "pack_type": "subject_content",
        "subject_id": "amc_middle_primary",
        "generated_at": datetime.now().isoformat(),
        "generation_mode": mode,
        "questions": questions,
        "assessment_sets": [{
            "assessment_set_key": f"amc-mp-set-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "name": f"AMC Practice — {mode.replace('_', ' ').title()}",
            "subject_id": "amc_middle_primary",
            "mode": mode,
            "ordered_question_keys": [q["question_key"] for q in questions],
            "total_marks": sum(q.get("marks", 3) for q in questions),
            "suggested_time_minutes": sum(q.get("suggested_time_minutes", 1) for q in questions),
        }]
    }
    
    output_path = output_dir / "content_pack.json"
    with open(output_path, "w") as f:
        json.dump(pack, f, indent=2)
    
    return output_path, pack


def main():
    parser = argparse.ArgumentParser(description="Generate AMC practice questions")
    parser.add_argument("--mode", default="quick", choices=["quick", "topic", "full"],
                       help="Generation mode")
    parser.add_argument("--topic", default=None,
                       help="Specific topic ID (e.g., money, time, arithmetic)")
    parser.add_argument("--count", type=int, default=None,
                       help="Number of questions to generate")
    parser.add_argument("--validate-only", action="store_true",
                       help="Only validate existing questions (no generation)")
    parser.add_argument("--output", default=None,
                       help="Output directory")
    args = parser.parse_args()
    
    if args.validate_only:
        # Load questions from stdin or file
        print("Validation-only mode not yet implemented for file input")
        return
    
    print(f"🧮 Generating {args.count or 'default'} AMC-style questions (mode: {args.mode})")
    if args.topic:
        print(f"   Topic: {args.topic}")
    
    # Generate
    questions = generate_batch(mode=args.mode, topic=args.topic, count=args.count)
    print(f"   Generated {len(questions)} questions")
    
    # Validate
    print("🔍 Validating answers...")
    validation = validate_batch(questions)
    
    print(f"   ✅ {validation['passed']} passed")
    print(f"   ❌ {validation['failed']} failed")
    
    if validation["failed"] > 0:
        print("\n   Failed validations:")
        for detail in validation["details"]:
            if detail["status"] == "fail":
                print(f"     • {detail['key']}: {detail['error']}")
    
    # Save
    if validation["passed"] > 0:
        output_path, pack = save_pack(questions, args.mode)
        print(f"\n💾 Saved to {output_path}")
        print(f"   Questions: {len(pack['questions'])}")
        print(f"   Total marks: {pack['assessment_sets'][0]['total_marks']}")
        print(f"   Time: {pack['assessment_sets'][0]['suggested_time_minutes']} min")
    
    print("\nDone!")


if __name__ == "__main__":
    main()
