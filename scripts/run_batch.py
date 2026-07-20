"""
Batch pipeline runner for SOP Mentor.

Discovers every (category / subcategory) leaf directory under --source-dir
and runs the full parse → extract → aggregate pipeline for each one,
writing separate, isolated output trees under --data-dir.

Expected source layout:
  <source-dir>/
    <category>/          e.g. STEM, 社科
      <subcategory>/     e.g. "personal statement", "writing sample", "其他"
        *.pdf / *.docx   (any depth)

Output layout produced:
  <data-dir>/
    <cat_slug>/
      <subcat_slug>/
        parsed/           ← Docling Markdown  (git-ignored)
        abstract/         ← DocumentAbstraction JSON files  (git-ignored)
        abstract/corpus_taxonomy.json

Usage:
  python scripts/run_batch.py \\
      --source-dir "C:/path/to/classified" \\
      [--data-dir data/batch] \\
      [--dry-run]          # preview LLM extraction without calling Ollama
      [--skip-extract]     # parse + aggregate only, skip LLM step
"""
from __future__ import annotations

import argparse
import logging
import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

log = logging.getLogger(__name__)

# Well-known Chinese/spaced folder names → ASCII slugs
_SLUG_MAP: dict[str, str] = {
    "其他": "other",
    "社科": "sheke",
    "stem": "STEM",
    "writing sample": "writing_sample",
    "personal statement": "personal_statement",
    "statement of purpose": "statement_of_purpose",
    "motivation letter": "motivation_letter",
    "research proposal": "research_proposal",
    "diversity statement": "diversity_statement",
}


def slugify(name: str) -> str:
    """Return a filesystem-safe slug for a folder name."""
    lower = name.strip().lower()
    if lower in _SLUG_MAP:
        return _SLUG_MAP[lower]
    # Generic fallback: keep the original name but replace spaces
    return re.sub(r"\s+", "_", name.strip()) or "unknown"


def count_source_files(source_dir: Path) -> int:
    return (
        len(list(source_dir.rglob("*.pdf")))
        + len(list(source_dir.rglob("*.docx")))
    )


def run_step(script: str, extra_args: list[str]) -> int:
    """
    Run a pipeline script as a subprocess from PROJECT_ROOT.
    Streams output directly to the console. Returns exit code.
    """
    cmd = [sys.executable, str(PROJECT_ROOT / "scripts" / script), *extra_args]
    log.debug("Running: %s", " ".join(str(c) for c in cmd))
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    return result.returncode


def run_pipeline(
    source_dir: Path,
    parsed_dir: Path,
    abstract_dir: Path,
    out_file: Path,
    dry_run: bool,
    skip_extract: bool,
) -> dict[str, str]:
    """
    Run parse → extract → aggregate for one (category, subcategory) pair.
    Returns {'parse': status, 'extract': status, 'aggregate': status}.
    """
    status: dict[str, str] = {}

    # ------------------------------------------------------------------ #
    # Step 1: Parse
    # ------------------------------------------------------------------ #
    rc = run_step(
        "parse_documents.py",
        ["--raw-dir", str(source_dir), "--out-dir", str(parsed_dir)],
    )
    status["parse"] = "OK" if rc == 0 else f"FAIL({rc})"
    if rc != 0:
        status["extract"] = "SKIP"
        status["aggregate"] = "SKIP"
        return status

    # ------------------------------------------------------------------ #
    # Step 2: Extract (optional)
    # ------------------------------------------------------------------ #
    if skip_extract:
        status["extract"] = "SKIPPED"
    else:
        extract_args = [
            "--parsed-dir", str(parsed_dir),
            "--abstract-dir", str(abstract_dir),
        ]
        if dry_run:
            extract_args.append("--dry-run")
        rc = run_step("extract_patterns.py", extract_args)
        status["extract"] = "OK" if rc == 0 else f"FAIL({rc})"
        if rc != 0:
            status["aggregate"] = "SKIP"
            return status

    # ------------------------------------------------------------------ #
    # Step 3: Aggregate
    # ------------------------------------------------------------------ #
    if skip_extract or dry_run:
        status["aggregate"] = "SKIPPED"
    else:
        rc = run_step(
            "aggregate_taxonomy.py",
            [
                "--abstract-dir", str(abstract_dir),
                "--out-file", str(out_file),
            ],
        )
        status["aggregate"] = "OK" if rc == 0 else f"FAIL({rc})"

    return status


def discover_pairs(source_dir: Path) -> list[tuple[str, str, Path]]:
    """Return [(cat_name, subcat_name, subcat_path)] for every leaf directory."""
    pairs: list[tuple[str, str, Path]] = []
    for cat_dir in sorted(source_dir.iterdir()):
        if not cat_dir.is_dir():
            continue
        for subcat_dir in sorted(cat_dir.iterdir()):
            if not subcat_dir.is_dir():
                continue
            pairs.append((cat_dir.name, subcat_dir.name, subcat_dir))
    return pairs


def _print_summary(
    results: list[tuple[str, str, int, dict[str, str]]],
    data_dir: Path,
) -> None:
    sep = "=" * 76
    fmt = "  {:<16} {:<28} {:>5}  {:<10} {:<10} {:<10}"
    print()
    print(sep)
    print("  BATCH PIPELINE SUMMARY")
    print(sep)
    print(fmt.format("Category", "Subcategory", "Files", "Parse", "Extract", "Aggregate"))
    print("-" * 76)
    for cat, subcat, n, st in results:
        print(fmt.format(
            cat[:16],
            subcat[:28],
            n,
            st.get("parse", "-"),
            st.get("extract", "-"),
            st.get("aggregate", "-"),
        ))
    print(sep)
    print(f"  Taxonomy outputs: {data_dir}/<category>/<subcategory>/abstract/corpus_taxonomy.json")
    print(sep)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run the full SOP Mentor pipeline for every category/subcategory "
            "found under the source directory."
        )
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        required=True,
        metavar="DIR",
        help="Root classified directory (contains category subdirectories).",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data/batch"),
        metavar="DIR",
        help="Base output directory for batch results (default: data/batch).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Pass --dry-run to extract_patterns (no LLM calls; parse still runs).",
    )
    parser.add_argument(
        "--skip-extract",
        action="store_true",
        help="Skip the LLM extraction step entirely. Useful to parse first and extract later.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    source_dir: Path = args.source_dir.resolve()
    if not source_dir.exists():
        log.error("Source directory not found: %s", source_dir)
        sys.exit(1)

    data_dir: Path = args.data_dir

    pairs = discover_pairs(source_dir)
    if not pairs:
        log.error("No category/subcategory directories found under %s", source_dir)
        sys.exit(1)

    log.info("Discovered %d subcategory pipeline(s):", len(pairs))
    for cat, subcat, path in pairs:
        log.info("  [%s / %s]  %d file(s)", cat, subcat, count_source_files(path))
    print()

    results: list[tuple[str, str, int, dict[str, str]]] = []

    for cat, subcat, subcat_path in pairs:
        cat_slug = slugify(cat)
        subcat_slug = slugify(subcat)
        n_files = count_source_files(subcat_path)

        parsed_dir = data_dir / cat_slug / subcat_slug / "parsed"
        abstract_dir = data_dir / cat_slug / subcat_slug / "abstract"
        out_file = abstract_dir / "corpus_taxonomy.json"

        parsed_dir.mkdir(parents=True, exist_ok=True)
        abstract_dir.mkdir(parents=True, exist_ok=True)

        log.info("━" * 60)
        log.info("Pipeline: [%s / %s]  (%d files)", cat, subcat, n_files)
        log.info("  source  → %s", subcat_path)
        log.info("  parsed  → %s", parsed_dir)
        log.info("  output  → %s", out_file)
        log.info("━" * 60)

        if n_files == 0:
            log.warning("No PDF/DOCX files in %s — skipping pipeline.", subcat_path)
            st: dict[str, str] = {
                "parse": "SKIP(empty)",
                "extract": "SKIP",
                "aggregate": "SKIP",
            }
        else:
            st = run_pipeline(
                source_dir=subcat_path,
                parsed_dir=parsed_dir,
                abstract_dir=abstract_dir,
                out_file=out_file,
                dry_run=args.dry_run,
                skip_extract=args.skip_extract,
            )

        results.append((cat, subcat, n_files, st))

    _print_summary(results, data_dir)


if __name__ == "__main__":
    main()
