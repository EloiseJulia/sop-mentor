# Safety and Privacy Policy

This policy governs all sop-mentor scripts, Copilot skill responses, and any
AI-assisted operations in this workspace.

---

## 1. Prohibited Content Operations

### 1.1 Content Reproduction
- Do NOT copy any sentence, clause, or phrase from sample essays into any output
- Do NOT paraphrase, summarise, or "translate" sample essay content in any form
- Do NOT produce text that describes what a specific sample essay is "about"

### 1.2 Identity Transfer
- Do NOT transfer personal stories, biographical facts, or experiences between authors
- Do NOT include names of people, institutions, projects, or advisors from sample essays
- Do NOT infer or expose the identity of any sample essay author
- Do NOT reveal the number of sample essays from any one institution or field
  if that count could identify an author

### 1.3 External Data Transmission
- Do NOT send raw or parsed essay text to external LLM APIs unless
  `allow_external_llm: true` is explicitly set in `config/privacy.yaml`
- Do NOT log essay body text at INFO level or above (log filenames and metrics only)
- Do NOT store essay text outside `data/raw-private/` and `data/parsed-private/`
- Do NOT include essay text in any git commit

---

## 2. Directory Access Boundaries

| Script | May Read | May Write |
|--------|----------|-----------|
| `parse_documents.py` | `data/raw-private/` | `data/parsed-private/` |
| `extract_patterns.py` | `data/parsed-private/` | `data/abstract/` |
| `aggregate_taxonomy.py` | `data/abstract/` **ONLY** | `data/abstract/corpus_taxonomy.json` |
| `check_originality.py` | `data/parsed-private/`, `data/user-private/` | stdout |

Violations of these boundaries should cause the script to exit with a non-zero
status and log an error — never silently continue.

---

## 3. check_originality.py Output Rules

The originality checker output MUST contain ONLY:
- Risk level (LOW / MEDIUM / HIGH / UNKNOWN)
- Aggregate numeric metrics (n-gram overlap %, token run length, file counts)
- Generic, non-identifying reasons (e.g. "high n-gram overlap detected")
- Suggested revision actions (generic)

The originality checker output MUST NEVER contain:
- Any matching text from sample essays or the user's draft
- Sample filenames, paths, or any identifier for a specific sample
- Information that narrows down which sample(s) contributed to a flag

---

## 4. Pydantic Schema Rules

- All models use `ConfigDict(extra="forbid")`
- No field may store: verbatim text, quotes, excerpts, story summaries,
  identifying proper nouns, or personal biographical details
- Field descriptions must explain what the field stores and what it must NOT store

---

## 5. Permitted Operations

- Extracting abstract structural metadata (word counts, section labels, arc labels)
- Generating generic keyword lists with no proper nouns
- Providing structural scaffolds built from the **user's own** supplied facts
- Reporting similarity metrics without revealing matching text or sample identities
- Aggregating counts and frequencies across the corpus

---

## 6. Incident Response

If a script accidentally outputs or logs essay content:
1. Delete the output file immediately
2. Do NOT commit the output to git
3. Verify `.gitignore` covers all relevant output directories
4. Review and fix the script logic before re-running
5. Consider auditing `git log --all --full-history -- data/` for accidental staging
