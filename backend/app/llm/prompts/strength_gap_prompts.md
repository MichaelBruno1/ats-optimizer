# Strength & Gap Specialist Prompts

## Strength Analyzer Prompt
Evaluate candidate profile against target job requirements to identify core strengths with concrete evidence from work experience.

Output schema:
```json
{
  "strengths": [
    {
      "item": "<string>",
      "importance": "<high|medium|low>",
      "evidence": "<concrete citation from resume experience>"
    }
  ]
}
```

## Gap Analyzer Prompt
Identify qualification gaps, missing skills, poorly described experience, and missing ATS keywords.
Differentiate:
1. Truly missing skill.
2. Skill present in experience but not explicitly named in skills list.
3. Equivalent skill possessed (e.g. Flask for FastAPI).

Output schema:
```json
{
  "gaps": [
    {
      "skill": "<string>",
      "gap_type": "<truly_missing|not_explicit|equivalent_possessed>",
      "explanation": "<string>",
      "equivalent_found": "<string or null>"
    }
  ],
  "missing_keywords": ["<string>"],
  "seniority_gap": "<string or null>"
}
```
