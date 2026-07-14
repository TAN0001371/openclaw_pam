# ScoreReady Integration Reference

## What needs to change in assessment-lab-web

### 1. `src/lib/subject-order.ts`

Add to the SUBJECT_ORDER array:
```typescript
export const SUBJECT_ORDER = [
  // ... existing subjects ...
  "amc_middle_primary",  // <-- ADD THIS (or place where you want in order)
] as const;
```

Add abbreviations:
```typescript
amc_middle_primary: ["AMC", "Maths Comp", "Middle Primary"],
```

Add short label:
```typescript
amc_middle_primary: "AMC Maths",
```

Add description:
```typescript
amc_middle_primary:
  "Australian Mathematics Competition practice for Years 3-4. Arithmetic, patterns, logic and problem solving.",
```

Add category:
```typescript
amc_middle_primary: "Mathematics",
```

Add colors (use orange/gold for AMC brand feel):
```typescript
amc_middle_primary: {
  bg: "bg-orange-50", text: "text-orange-700", border: "border-orange-200",
  ring: "ring-orange-200", hex: "#f97316",
  gradient: "linear-gradient(180deg, rgba(249,115,22,0.12) 0%, ...)",
  categoryLabel: "Mathematics",
},
```

### 2. `src/lib/subject-theme.ts`

Add theme:
```typescript
amc_middle_primary: {
  label: "AMC Maths",
  border: "border-orange-200",
  soft: "bg-orange-50/75",
  text: "text-orange-700",
  accent: "bg-orange-500",
  badge: "bg-orange-50 text-orange-700 ring-orange-200",
  card: "border-orange-200 bg-gradient-to-br from-white via-orange-50/85 to-amber-50/75 hover:border-orange-400",
  glow: "shadow-[0_22px_48px_rgba(249,115,22,0.22)]",
  previewGradient: "from-orange-400/22 to-amber-400/10 border-orange-300/28",
  icon: "bg-orange-100 text-orange-800",
},
```

### 3. Supabase `subjects` table

Insert a new row:
```sql
INSERT INTO subjects (subject_id, name, short_name, status, active_study_design_version)
VALUES ('amc_middle_primary', 'AMC Middle Primary (Years 3-4)', 'AMC Maths', 'active', 'current');
```

### 4. Content import

Use the admin content import tool at `/admin/content/import` to upload
generated `content_pack.json` files from the AMC pipeline.

### 5. Promo code gating (optional)

Two approaches:
- **Simple**: Add `amc_middle_primary` to a hidden subject list that only appears when user has a promo code applied
- **Proper**: Add a `required_promo_code` field to subjects table, check in the subject picker

---

## Pipeline (already built in pam_repo/amc/)

1. `generate.py` — creates AMC questions via Gemini
2. `math_validator.py` — independently verifies every answer
3. Output: content_pack.json ready for import

Run: `python3 amc/generate.py --count 10` → import result into ScoreReady.
