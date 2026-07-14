# AMC Papers Handoff — for Claude Code

## What This Is

Archive of Australian Mathematics Competition (AMC) Middle Primary (Years 3-4) past papers:
- Papers transcribed from images via Gemini Vision API
- Answer keys compiled from official answer sheets and solution booklets
- Math independently verified programmatically

## Where Everything Lives

```
GitHub: https://github.com/TAN0001371/openclaw_pam
Local:  /home/pam/.openclaw/workspace/pam_repo/

Key paths:
  amc_papers/          ← Organized paper archive
    2016/  README.md  questions/  solutions/    ← COMPLETE
    2017/  README.md  questions/  solutions/    ← COMPLETE
    2018/  README.md  questions/  solutions/    ← 95% complete
    2019/  README.md  questions/  solutions/    ← PARTIAL (handwritten)
    2020/  README.md  questions/  solutions/    ← Answer key complete, needs labeling
  
  amc/                 ← Generation pipeline
    generate.py        ← Question generator (Gemini + validator)
    math_validator.py  ← Independent answer verification
    batch_parallel.py  ← Fast parallel transcription (~8s per paper)
    config/            ← AMC Middle Primary subject config
    INTEGRATION.md     ← ScoreReady integration reference
```

## Goal

Build an AMC practice section on ScoreReady for Stewart's son Leo:
1. Use transcribed past papers as reference data for style, difficulty, and topic distribution
2. Generate ORIGINAL questions in the AMC style (not copies — copyright)
3. Two-AI review: different models must agree on answers before a question is published
4. Diagrams rendered as structured SVGs from media_spec data (no AI image generation)

## Math Audit Results

All answers independently verified. Full audit at `amc_audit/audit_results.json`.

| Year | Status | Notes |
|------|--------|-------|
| 2016 | ✅ All 30 verified | Math checks out |
| 2017 | ✅ All 30 verified | From printed solutions |
| 2018 | ✅ All 30 verified | Q24/E and Q26/16 from paraphrased source — needs cross-check |
| 2019 | ⚠ Partial | Handwritten solutions — handwriting recognition unreliable |
| 2020 | ✅ Answer key verified | Official AMT answer sheet |
```

## Issues & Concerns

### 1. Transcription Quality
- Most printed pages: 95%+ accurate
- Handwritten 2019 solutions: 60-70% accurate at best — HUMAN REVIEW NEEDED
- Some pages hit Gemini's copyright RECITATION filter → paraphrased instead of verbatim
- Paraphrased pages (~3-4 across all years) have answers but lack full solution detail

### 2. Handwritten Content (2019)
- Q28 answer "162" — verified correct (18 zeros × 9 centuries = 162)
- Q29 answer "224" — verified correct (2016 ÷ 9 = 224)
- Q30 answer incomplete — transcription cut off mid-sentence
- Other handwritten solutions not fully transcribed
- ACTION: Stewart should manually review 2019 solutions

### 3. Copyright Risk
- Gemini flagged 4-5 pages across years as matching copyrighted content on Scribd/dokumen.pub
- Educational-use argument is strong (son's practice, not commercial reproduction)
- But the factory-generated questions must be ORIGINAL, not copies

### 4. Question Generation Quality
- Pipeline tested: 7/8 questions passed validation on first run
- Failure was formatting ($10.00 vs 10.0), not math error
- Risk areas: question uniqueness (multiple valid answers), ambiguous wording
- Mitigation: TWO different AI models must independently solve each generated question
```

## Two-AI Review System

When generating content in the factory, the following should happen:

1. **Generate**: Gemini creates a question with answer and validator expression
2. **Validate**: math_validator.py independently computes the answer (Python, no AI)
3. **Cross-check**: A SECOND AI model (Claude or OpenAI/Grok) independently solves the question
4. **Agree**: Both models must agree on the answer, or the question is re-generated
5. **Audit**: Claude's auditor prompt checks for question quality, uniqueness, ambiguity

This gives us: Gemini generates → Python validates math → Claude/Grok independently solves → Claude audits quality.

## Transcription Pipeline

```
Images → batch_parallel.py → Gemini Vision API (parallel, 8 concurrent)
       → Saves to amc_papers/{year}/
       → README.md with answer key
```

API key: stored in `.gemini_key` (not in git)
Model: gemini-3.1-flash-lite (free tier, fastest)

## ScoreReady Integration

The subject config (`amc/config/amc_middle_primary.json`) and generator are ready.
Integration steps documented in `amc/INTEGRATION.md`:
1. Add `amc_middle_primary` to `subject-order.ts` and `subject-theme.ts`
2. Add subject row to Supabase
3. Import generated content packs through admin panel
4. Gate behind promo code for Leo (+ friends)

## What Stewart Still Needs To Do

1. Review 2019 handwritten solutions (images are in Telegram, not all saved locally)
2. Decide if 2019 is worth full transcription (handwritten = unreliable)
3. Run the content factory at home (DeepSeek API needed, can't use at work)
4. Provide 2020 page MP labels so I can rename raw_XX files
