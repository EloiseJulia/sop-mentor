# SOP Mentor

A **local-first** pipeline for analyzing graduate application essay samples at an
abstract structural level. It extracts writing patterns — never essay content —
and helps you write original essays from your own facts and experiences.

> **Privacy guarantee:** No essay text is committed to git, logged at INFO level,
> or sent to external services by default. All LLM calls use a local Ollama instance.

---

## Privacy Architecture

```
data/raw-private/     ← Your private PDF/DOCX samples     (git-ignored)
data/parsed-private/  ← Intermediate Markdown             (git-ignored)
data/abstract/        ← Abstract JSON pattern records     (git-ignored)
data/user-private/    ← Your draft essays                 (git-ignored)
```

All four directories are excluded from git. Only structural metadata (counts, arc
labels, rhetorical move labels) is ever written to `data/abstract/`.

---

## Setup

### 1. Prerequisites
- Python 3.10 or later
- [Ollama](https://ollama.com) running locally with the `llama3.2` model

```bash
ollama pull llama3.2
ollama serve          # keep running in a separate terminal
```

### 2. Install the project

```bash
cd "sop mentor"
pip install -e ".[dev]"
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env only if you need to override OLLAMA_BASE_URL or add OPENAI_API_KEY
```

### 4. (Optional) Allow external LLM

Edit `config/privacy.yaml` and set `allow_external_llm: true`. Then add your
`OPENAI_API_KEY` to `.env`.

---

## Run Sequence

```bash
# 1. Place your PDF or DOCX essay samples in:
#       data/raw-private/

# 2. Parse documents to Markdown
python scripts/parse_documents.py

# 3. Preview extraction without calling the LLM
python scripts/extract_patterns.py --dry-run

# 4. Extract abstract patterns (calls Ollama)
python scripts/extract_patterns.py

# 5. Aggregate the corpus taxonomy
python scripts/aggregate_taxonomy.py

# 6. Check your draft for token-level similarity to the samples
python scripts/check_originality.py --draft data/user-private/my-draft.md
```

---

## Privacy Boundaries

| Boundary | Rule |
|----------|------|
| Git | `data/raw-private/`, `data/parsed-private/`, `data/user-private/`, `data/abstract/` are all git-ignored |
| Logging | Scripts log filenames and size metrics only — never document body text |
| LLM provider | Local Ollama by default; set `allow_external_llm: true` in `config/privacy.yaml` to use external APIs |
| Pydantic schemas | `extra="forbid"` on all models; no fields for verbatim text or identifying details |
| Originality report | Only risk level, metrics, and generic reasons — never matching text or sample filenames |
| Aggregation | `aggregate_taxonomy.py` reads `data/abstract/` only; never touches raw or parsed data |

---

## Copilot Chat Usage

Once the pipeline has been run, use GitHub Copilot Chat in this workspace:

```
@workspace What narrative arc patterns are most common in the corpus?

@workspace Using the sop-mentor skill, help me outline a CS PhD statement of purpose.

@workspace Evaluate the structural coherence of my draft below.

@workspace What rhetorical moves typically appear in high-research-emphasis essays?

@workspace Show me the section_order distribution from the corpus taxonomy.
```

Copilot will use `.github/copilot-instructions.md` and the skill files in
`.github/skills/sop-mentor/` to apply the safety rules automatically.

---

## Schema Overview

### `DocumentAbstraction` (`schemas/document_analysis.py`)
Abstract metadata for one essay. Contains no verbatim text.

| Field | Type | Description |
|-------|------|-------------|
| `doc_id` | `str` | Filename stem — no PII |
| `program_type` | `ProgramType` | `phd` / `masters` / `professional` / `unknown` |
| `field_of_study` | `str` | Generic field label |
| `word_count` | `int` | Approximate word count |
| `structure` | `EssayStructurePattern` | Section order, opening/closing moves, paragraph count |
| `writing_patterns` | `AbstractWritingPattern` | Arc, motivation placement, research emphasis |
| `rhetorical_moves` | `list[str]` | Ordered abstract move labels |
| `theme_keywords` | `list[str]` | Generic topical keywords (no proper nouns) |

### `CorpusTaxonomy` (`schemas/corpus_taxonomy.py`)
Aggregated taxonomy of the full corpus.

---

## Directory Structure

```
sop mentor/
├── .github/
│   ├── copilot-instructions.md
│   └── skills/sop-mentor/
│       ├── SKILL.md
│       └── references/
│           ├── rubric.md
│           ├── taxonomy.md
│           └── safety-policy.md
├── config/
│   ├── extraction.yaml
│   └── privacy.yaml
├── data/
│   ├── abstract/          (git-ignored)
│   ├── parsed-private/    (git-ignored)
│   ├── raw-private/       (git-ignored)
│   └── user-private/      (git-ignored)
├── schemas/
│   ├── __init__.py
│   ├── corpus_taxonomy.py
│   └── document_analysis.py
├── scripts/
│   ├── aggregate_taxonomy.py
│   ├── check_originality.py
│   ├── extract_patterns.py
│   └── parse_documents.py
├── tests/
│   └── fixtures-synthetic/
├── .env.example
├── .gitignore
├── pyproject.toml
└── README.md
```
