"""
Extract abstract writing patterns from parsed Markdown files.

Reads:  data/parsed-private/*.md
Writes: data/abstract/<stem>.json  (DocumentAbstraction JSON)

Privacy enforcement:
  - Default provider is ollama/llama3.2 (local, no data leaves the machine)
  - External LLM providers are BLOCKED unless config/privacy.yaml sets
    allow_external_llm: true explicitly
  - Document body is sent to the LLM but never written to logs

Flags:
  --dry-run   Preview which files would be processed without calling the LLM
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

import yaml

# Ensure the project root is on sys.path so 'schemas' is importable
# when the script is run directly (python scripts/extract_patterns.py)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from schemas.document_analysis import DocumentAbstraction  # noqa: E402

PARSED_DIR = Path("data/parsed-private")
ABSTRACT_DIR = Path("data/abstract")
PRIVACY_CONFIG = Path("config/privacy.yaml")
EXTRACTION_CONFIG = Path("config/extraction.yaml")

log = logging.getLogger(__name__)


def _load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def resolve_provider(privacy: dict, extraction: dict) -> tuple[str, str]:
    """
    Return (base_url, model) after enforcing the privacy policy.

    Exits with a non-zero status if an external provider is requested
    but allow_external_llm is not explicitly set to true.
    """
    provider: str = extraction.get("provider", "ollama/llama3.2")
    allow_external: bool = bool(privacy.get("allow_external_llm", False))

    if provider.startswith("ollama/"):
        model = provider[len("ollama/"):]
        base_url: str = str(
            extraction.get("ollama_base_url", "http://localhost:11434/v1")
        )
        return base_url, model

    # Non-Ollama provider — blocked unless explicitly allowed
    if not allow_external:
        log.error(
            "External LLM provider '%s' is blocked by default. "
            "Set allow_external_llm: true in config/privacy.yaml to enable.",
            provider,
        )
        sys.exit(1)

    return "https://api.openai.com/v1", provider


def build_client(base_url: str) -> object:
    """Construct an instructor-wrapped OpenAI-compatible client."""
    try:
        import instructor
        from openai import OpenAI
    except ImportError as exc:
        log.error(
            "Missing dependency: %s — install with: pip install -e .", exc
        )
        sys.exit(1)

    if "11434" in base_url:
        raw = OpenAI(base_url=base_url, api_key="ollama")
    else:
        # For external providers the key is read from OPENAI_API_KEY env var
        raw = OpenAI(base_url=base_url)

    return instructor.from_openai(raw)


def extract_for_file(
    client: object,
    model: str,
    md_path: Path,
    extraction: dict,
    dry_run: bool,
) -> Optional[DocumentAbstraction]:
    """Extract abstract patterns from one Markdown file."""
    doc_id = md_path.stem

    if dry_run:
        log.info("[dry-run] Would extract patterns for: %s", md_path.name)
        return None

    md_text = md_path.read_text(encoding="utf-8")

    # Respect max_input_chars limit
    max_chars: int = int(extraction.get("max_input_chars", 16000))
    if len(md_text) > max_chars:
        log.warning(
            "%s truncated from %d to %d chars for LLM input",
            md_path.name, len(md_text), max_chars,
        )
        md_text = md_text[:max_chars]

    system_prompt = (
        "You are a structural writing analyst. "
        "Extract ONLY abstract writing patterns from the provided graduate application essay. "
        "Do NOT reproduce any sentences, phrases, personal stories, research project details, "
        "proper nouns, or identifying information from the source text. "
        "Return structured metadata only."
    )
    user_prompt = (
        f"Analyze this graduate application essay and return a DocumentAbstraction "
        f"with doc_id='{doc_id}'.\n\nEssay:\n{md_text}"
    )

    max_retries: int = int(extraction.get("retries", 2))

    return client.chat.completions.create(  # type: ignore[attr-defined]
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_model=DocumentAbstraction,
        max_retries=max_retries,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract abstract writing patterns from parsed Markdown files."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List files to process without calling the LLM.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    privacy = _load_yaml(PRIVACY_CONFIG)
    extraction = _load_yaml(EXTRACTION_CONFIG)

    client: object = None
    model: str = ""

    if not args.dry_run:
        base_url, model = resolve_provider(privacy, extraction)
        client = build_client(base_url)

    ABSTRACT_DIR.mkdir(parents=True, exist_ok=True)

    md_files = list(PARSED_DIR.glob("*.md"))
    if not md_files:
        log.warning("No .md files found in %s", PARSED_DIR)
        return

    log.info(
        "Processing %d file(s)%s",
        len(md_files),
        " (dry-run)" if args.dry_run else "",
    )

    min_words: int = int(extraction.get("min_word_count", 100))
    success, failure, skipped = 0, 0, 0

    for md_path in md_files:
        try:
            # Skip files below minimum word count
            word_count = len(md_path.read_text(encoding="utf-8").split())
            if word_count < min_words:
                log.warning(
                    "Skipping %s: only %d words (min %d)",
                    md_path.name, word_count, min_words,
                )
                skipped += 1
                continue

            result = extract_for_file(client, model, md_path, extraction, args.dry_run)
            if result is not None:
                out_path = ABSTRACT_DIR / f"{md_path.stem}.json"
                out_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                log.info("Wrote %s", out_path.name)
            success += 1
        except Exception as exc:  # noqa: BLE001
            log.error("Failed on %s: %s", md_path.name, exc)
            failure += 1

    log.info(
        "Done: %d succeeded, %d failed, %d skipped",
        success, failure, skipped,
    )


if __name__ == "__main__":
    main()
