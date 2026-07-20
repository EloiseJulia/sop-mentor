# GitHub Copilot Instructions — SOP Mentor

## Project Overview
SOP Mentor is a **local-first** pipeline for analyzing graduate application essay samples
at an abstract structural level. It extracts writing patterns — never essay content —
and helps users write original essays from their own facts and experiences.

## Core Safety Rules

### 1. No Content Reproduction
Do NOT suggest, generate, or complete code that:
- Outputs verbatim or paraphrased sentences/phrases from sample essays
- Transfers personal stories, experiences, or biographical details between authors
- Creates fields or variables that store source quotes, excerpts, or sample text

### 2. Privacy-by-Default
- All LLM calls MUST use the local Ollama provider unless `config/privacy.yaml` sets
  `allow_external_llm: true`
- Document body text must never appear in logs at INFO level or above
- Essay text must never be committed to git (covered by `.gitignore`)

### 3. Schema Discipline
- All Pydantic models use `ConfigDict(extra="forbid")`
- Never add fields for: source text, quotes, excerpts, identifying details, story summaries
- Use abstract labels (e.g. `"hook_question"`) — never the actual text

### 4. Directory Isolation
Each script must access ONLY its designated directories:

| Script | Reads | Writes |
|--------|-------|--------|
| `parse_documents.py` | `data/raw-private/` | `data/parsed-private/` |
| `extract_patterns.py` | `data/parsed-private/` | `data/abstract/` |
| `aggregate_taxonomy.py` | `data/abstract/` ONLY | `data/abstract/corpus_taxonomy.json` |
| `check_originality.py` | `data/parsed-private/`, `data/user-private/` | stdout |

### 5. Output Safety for check_originality.py
The originality checker must NEVER output:
- Matching text from samples or the draft
- Sample filenames or paths
- Any information that could identify a specific sample essay author

## Code Style Conventions
- Python 3.10+, type hints required
- Pydantic v2 — `ConfigDict(extra="forbid")`, `model_dump_json()`, `model_validate()`
- `from __future__ import annotations` at the top of every module
- Standard library `logging` (not `print`) for diagnostic output
- `pathlib.Path` for all file operations
- `argparse` for CLI arguments
- Continue on per-file errors; never abort the full run for one bad file

## When Copilot Suggests Changes
- Preserve the privacy boundaries and directory isolation rules above
- Do not simplify schemas by adding free-text or prose fields
- Do not suggest sending data to external APIs without checking `allow_external_llm`
- Do not add dependencies not listed in `pyproject.toml` without noting the addition
