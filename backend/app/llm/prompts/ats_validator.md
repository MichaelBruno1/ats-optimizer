# ATS Validator Prompt

Audit an optimized resume against the original raw resume text and target job description.

## Audit Criteria:
1. Anti-Hallucination: Check if any new skill, title, employer, or certification was fabricated.
2. Keyword Naturalness: Ensure keywords are woven in naturally without keyword stuffing.
3. Clarity & Quality: Ensure professional summary and bullet points follow high quality executive standards.

Output Schema:
```json
{
  "approved": <true|false>,
  "validation_score": <int 0-100>,
  "hallucination_detected": <true|false>,
  "issues": [
    {
      "severity": "<error|warning|info>",
      "category": "<anti_hallucination|ats_format|keyword_stuffing|content_quality>",
      "message": "<string>",
      "field_affected": "<string>"
    }
  ],
  "validation_errors": ["<string>"],
  "validation_warnings": ["<string>"]
}
```
