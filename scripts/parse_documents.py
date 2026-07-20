"""
Parse PDF and DOCX files from data/raw-private/ → Markdown + metadata JSON
in data/parsed-private/.

Behaviour:
  - Scans data/raw-private/ recursively for .pdf and .docx files
  - Converts each file to Markdown using Docling
  - Writes <stem>.md and <stem>.meta.json to data/parsed-private/
  - Logs filenames and size metrics ONLY — never the document body
  - Continues on per-file failure; reports a summary at the end
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

from docling.document_converter import DocumentConverter

RAW_DIR = Path("data/raw-private")
OUT_DIR = Path("data/parsed-private")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)


def parse_document(converter: DocumentConverter, src: Path, out_dir: Path) -> None:
    """Convert one file and write Markdown + metadata JSON to out_dir."""
    result = converter.convert(str(src))
    md_text: str = result.document.export_to_markdown()

    stem = src.stem
    out_md = out_dir / f"{stem}.md"
    out_meta = out_dir / f"{stem}.meta.json"

    out_md.write_text(md_text, encoding="utf-8")

    metadata: dict[str, object] = {
        "source_filename": src.name,
        "source_suffix": src.suffix,
        "char_count": len(md_text),
        "word_count_approx": len(md_text.split()),
    }
    if hasattr(result.document, "page_count"):
        metadata["page_count"] = result.document.page_count

    out_meta.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    # Log metrics only — the document body is intentionally not logged
    log.info(
        "Parsed %s → %s  (%d chars, ~%d words)",
        src.name,
        out_md.name,
        metadata["char_count"],
        metadata["word_count_approx"],
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    files: list[Path] = (
        list(RAW_DIR.rglob("*.pdf")) + list(RAW_DIR.rglob("*.docx"))
    )

    if not files:
        log.warning("No PDF or DOCX files found under %s", RAW_DIR)
        return

    log.info("Found %d file(s) to parse", len(files))
    converter = DocumentConverter()
    success, failure = 0, 0

    for src in files:
        try:
            parse_document(converter, src, OUT_DIR)
            success += 1
        except Exception as exc:  # noqa: BLE001
            log.error("Failed to parse %s: %s", src.name, exc)
            failure += 1

    log.info("Finished: %d succeeded, %d failed", success, failure)


if __name__ == "__main__":
    main()
