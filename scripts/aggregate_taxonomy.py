"""
Aggregate abstract corpus taxonomy from data/abstract/*.json only.

Reads:  data/abstract/<stem>.json  (DocumentAbstraction records)
Writes: data/abstract/corpus_taxonomy.json  (CorpusTaxonomy)

SAFETY CONSTRAINT: This script MUST NOT read from data/raw-private/
or data/parsed-private/. Only data/abstract/*.json is permitted.
The script enforces this with a runtime path check.
"""
from __future__ import annotations

import json
import logging
import sys
from collections import Counter
from pathlib import Path

# Ensure the project root is on sys.path so 'schemas' is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from schemas.corpus_taxonomy import ArcFrequency, CorpusTaxonomy  # noqa: E402
from schemas.document_analysis import DocumentAbstraction  # noqa: E402

ABSTRACT_DIR = Path("data/abstract")
TAXONOMY_OUT = ABSTRACT_DIR / "corpus_taxonomy.json"

# Directories this script must never read from
_FORBIDDEN_DIRS = (
    Path("data/raw-private").resolve(),
    Path("data/parsed-private").resolve(),
)

log = logging.getLogger(__name__)


def _assert_not_forbidden(path: Path) -> None:
    """Raise RuntimeError if path falls inside a forbidden directory."""
    resolved = path.resolve()
    for forbidden in _FORBIDDEN_DIRS:
        try:
            resolved.relative_to(forbidden)
            raise RuntimeError(
                f"aggregate_taxonomy.py attempted to read from forbidden "
                f"directory '{forbidden}'. Aborting."
            )
        except ValueError:
            pass  # path is not under this forbidden dir — continue


def load_abstractions(abstract_dir: Path) -> list[DocumentAbstraction]:
    """Load all DocumentAbstraction records from abstract_dir/*.json."""
    json_files = [
        p for p in abstract_dir.glob("*.json")
        if p.name != TAXONOMY_OUT.name
    ]

    records: list[DocumentAbstraction] = []
    for p in json_files:
        _assert_not_forbidden(p)
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            records.append(DocumentAbstraction.model_validate(data))
        except Exception as exc:  # noqa: BLE001
            log.error("Failed to load %s: %s", p.name, exc)

    return records


def build_taxonomy(records: list[DocumentAbstraction]) -> CorpusTaxonomy:
    n = len(records)

    program_counts: dict[str, int] = dict(
        Counter(r.program_type.value for r in records)
    )
    field_counts: dict[str, int] = dict(
        Counter(r.field_of_study for r in records)
    )
    arc_counter = Counter(r.writing_patterns.narrative_arc.value for r in records)
    arc_distribution = [
        ArcFrequency(arc=arc, count=count, frequency=count / n)
        for arc, count in arc_counter.most_common()
    ]

    all_moves: list[str] = [
        move for r in records for move in r.rhetorical_moves
    ]
    all_keywords: list[str] = [
        kw for r in records for kw in r.theme_keywords
    ]

    top_moves = [m for m, _ in Counter(all_moves).most_common(20)]
    top_keywords = [kw for kw, _ in Counter(all_keywords).most_common(30)]

    avg_word_count = sum(r.word_count for r in records) / n
    avg_paragraph_count = (
        sum(r.structure.paragraph_count for r in records) / n
    )
    pct_future = sum(
        1 for r in records if r.writing_patterns.future_goals_explicit
    ) / n
    pct_inter = sum(
        1 for r in records if r.writing_patterns.interdisciplinary
    ) / n

    return CorpusTaxonomy(
        total_documents=n,
        program_type_counts=program_counts,
        field_counts=field_counts,
        narrative_arc_distribution=arc_distribution,
        top_rhetorical_moves=top_moves,
        top_theme_keywords=top_keywords,
        avg_word_count=avg_word_count,
        avg_paragraph_count=avg_paragraph_count,
        pct_future_goals_explicit=pct_future,
        pct_interdisciplinary=pct_inter,
    )


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    records = load_abstractions(ABSTRACT_DIR)
    if not records:
        log.warning(
            "No valid DocumentAbstraction records found in %s — nothing to aggregate.",
            ABSTRACT_DIR,
        )
        return

    log.info("Aggregating taxonomy from %d record(s)", len(records))
    taxonomy = build_taxonomy(records)

    ABSTRACT_DIR.mkdir(parents=True, exist_ok=True)
    TAXONOMY_OUT.write_text(taxonomy.model_dump_json(indent=2), encoding="utf-8")
    log.info(
        "Wrote corpus taxonomy (%d documents) → %s",
        taxonomy.total_documents,
        TAXONOMY_OUT,
    )


if __name__ == "__main__":
    main()
