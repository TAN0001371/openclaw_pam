#!/usr/bin/env python3
"""
Parallel AMC paper transcriber — fires all API calls simultaneously.
Transcribes an entire paper in ~15 seconds instead of 2+ minutes.
"""
import json, base64, urllib.request, urllib.parse, sys, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

KEY_FILE = Path("/home/pam/.openclaw/workspace/.gemini_key")
MODEL = "gemini-3.1-flash-lite"

PROMPT = (
    "Transcribe ALL text and questions from this AMC Middle Primary (Years 3-4) past paper page. "
    "Include question numbers, full question text, all answer options A-E, and describe any diagrams in detail. "
    "Include any headers, instructions, page numbers, and footers."
)

def transcribe_one(img_path, key, idx):
    """Transcribe a single image. Returns (idx, text, error)."""
    try:
        with open(img_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()
        
        params = urllib.parse.urlencode({"key": key})
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?{params}"
        
        payload = {
            "contents": [{"parts": [
                {"text": PROMPT},
                {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}}
            ]}]
        }
        
        req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
        
        with urllib.request.urlopen(req, timeout=90) as resp:
            result = json.loads(resp.read())
        
        finish = result["candidates"][0].get("finishReason", "STOP")
        
        if finish != "STOP":
            # Try with educational prompt if recitation-blocked
            return transcribe_one_safe(img_path, key, idx)
        
        text = result["candidates"][0]["content"]["parts"][0]["text"]
        return (idx, text, None)
        
    except Exception as e:
        # Try safe fallback for KeyError('parts')
        if "parts" in str(e) or "KeyError" in str(e):
            return transcribe_one_safe(img_path, key, idx)
        return (idx, None, str(e))


def transcribe_one_safe(img_path, key, idx):
    """Fallback: paraphrasing prompt for copyright-blocked pages."""
    try:
        with open(img_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()
        
        params = urllib.parse.urlencode({"key": key})
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?{params}"
        
        safe_prompt = (
            "You are helping create educational tutoring materials. "
            "Extract the mathematical content from this AMC Year 3-4 paper page. "
            "For each question: note the number, paraphrase the problem, state the answer options, and note the correct answer. "
            "Describe any diagrams. Do NOT copy text verbatim."
        )
        
        payload = {
            "contents": [{"parts": [
                {"text": safe_prompt},
                {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}}
            ]}]
        }
        
        req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
        
        with urllib.request.urlopen(req, timeout=90) as resp:
            result = json.loads(resp.read())
        
        text = result["candidates"][0]["content"]["parts"][0]["text"]
        return (idx, "[PARAPHRASED] " + text, None)
        
    except Exception as e:
        return (idx, None, str(e))


def batch_transcribe(image_paths, out_dir, label=""):
    """Transcribe all images in parallel. Returns list of (filename, text)."""
    with open(KEY_FILE) as f:
        api_key = f.read().strip()

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    results = {}
    errors = []
    
    with ThreadPoolExecutor(max_workers=min(8, len(image_paths))) as executor:
        futures = {executor.submit(transcribe_one, p, api_key, i): i for i, p in enumerate(image_paths, 1)}
        
        for future in as_completed(futures):
            idx, text, error = future.result()
            if error:
                errors.append((idx, error))
                print(f"  [{idx}/{len(image_paths)}] ✗ {error}")
            else:
                name = f"{label}page_{idx:02d}.txt" if label else f"page_{idx:02d}.txt"
                out_path = out_dir / name
                out_path.write_text(text, encoding="utf-8")
                results[idx] = name
        
    return results, errors


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 batch_parallel.py <year> <image_dir_or_files...>")
        print("  First 8 newest images become questions/, next 5 become solutions/")
        print("  python3 batch_parallel.py 2018")
        sys.exit(1)
    
    year = sys.argv[1]
    today = time.strftime("%Y%m%d")
    
    # Find all images from today
    all_imgs = sorted(
        Path("/home/pam/.openclaw/media/inbound").glob("*.jpg"),
        key=lambda p: p.stat().st_mtime, reverse=True
    )
    
    # Take only today's images
    today_imgs = [p for p in all_imgs if time.strftime("%Y%m%d", time.localtime(p.stat().st_mtime)) == today]
    
    if len(today_imgs) < 8:
        print(f"Not enough images for a full paper (found {len(today_imgs)} from today)")
        sys.exit(1)
    
    # Split: questions (first 8), solutions (rest)
    question_imgs = today_imgs[-8:]  # oldest 8 are usually questions
    solution_imgs = today_imgs[:len(today_imgs) - 8]  # newer ones are solutions
    
    base = Path(f"/home/pam/.openclaw/workspace/amc_{year}")
    
    print(f"📄 {year} AMC Middle Primary — {len(question_imgs)} questions + {len(solution_imgs)} solutions")
    print(f"⚡ Parallel mode: all calls fired simultaneously\n")
    
    t0 = time.time()
    
    # Fire both question and solution batches in parallel
    q_results = []
    s_results = []
    
    with ThreadPoolExecutor(max_workers=2) as batch_exec:
        q_future = batch_exec.submit(batch_transcribe, question_imgs, f"{base}/questions")
        s_future = batch_exec.submit(batch_transcribe, solution_imgs, f"{base}/solutions") if solution_imgs else None
        
        if s_future:
            q_results, q_errs = q_future.result()
            s_results, s_errs = s_future.result()
        else:
            q_results, q_errs = q_future.result()
            s_results, s_errs = [], []
    
    elapsed = time.time() - t0
    
    print(f"\n✅ Done in {elapsed:.1f}s")
    print(f"   Questions: {len(q_results)} succeeded, {len(q_errs)} errors")
    print(f"   Solutions: {len(s_results)} succeeded, {len(s_errs)} errors")
    print(f"   Saved to: {base}/")
