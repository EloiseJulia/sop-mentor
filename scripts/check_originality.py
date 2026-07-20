"""
Check a user draft essay for token-level similarity against the parsed sample corpus.

Reads:
  --draft <path>          Your draft file (plain text or Markdown)
  data/parsed-private/    Sample corpus Markdown files (never revealed in output)

Output (printed to stdout):
  - Risk level (LOW / MEDIUM / HIGH / UNKNOWN)
  - Aggregate metrics (n-gram overlap %, longest common token run, file counts)
  - Generic reasons (no sample text, no sample filenames)
  - Suggested actions

This script NEVER outputs:
  - Matching text from samples or the draft
  - Sample filenames or any information that identifies a specific sample
"""
from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path
from typing import Optional

PARSED_DIR = Path("data/parsed-private")

# Risk thresholds (tune as needed)
_HIGH_OVERLAP_THRESHOLD: float = 0.15   # >15 % 5-gram overlap → HIGH
_MEDIUM_OVERLAP_THRESHOLD: float = 0.05  # 5–15 % → MEDIUM
_HIGH_RUN_THRESHOLD: int = 16            # common token run ≥ 16 → HIGH
_MEDIUM_RUN_THRESHOLD: int = 8           # common token run 8–15 → MEDIUM

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tokenisation helpers
# ---------------------------------------------------------------------------

def tokenize(text: str) -> list[str]:
    """Return a list of lowercase word tokens."""
    return re.findall(r"\b\w+\b", text.lower())


def ngram_overlap(tokens_a: list[str], tokens_b: list[str], n: int = 5) -> float:
    """Fraction of n-grams in tokens_a that also appear in tokens_b."""
    if len(tokens_a) < n or len(tokens_b) < n:
        return 0.0
    ngrams_a = set(zip(*[tokens_a[i:] for i in range(n)]))
    ngrams_b = set(zip(*[tokens_b[i:] for i in range(n)]))
    if not ngrams_a:
        return 0.0
    return len(ngrams_a & ngrams_b) / len(ngrams_a)


def longest_common_token_run(tokens_a: list[str], tokens_b: list[str]) -> int:
    """Length of the longest contiguous run of identical tokens shared by both lists."""
    n = len(tokens_b)
    dp = [0] * (n + 1)
    max_run = 0
    for token_a in tokens_a:
        new_dp = [0] * (n + 1)
        for j, token_b in enumerate(tokens_b):
            if token_a == token_b:
                new_dp[j + 1] = dp[j] + 1
                if new_dp[j + 1] > max_run:
                    max_run = new_dp[j + 1]
        dp = new_dp
    return max_run


# ---------------------------------------------------------------------------
# Risk classification
# ---------------------------------------------------------------------------

def classify_risk(max_overlap: float, max_run: int) -> str:
    if max_overlap >= _HIGH_OVERLAP_THRESHOLD or max_run >= _HIGH_RUN_THRESHOLD:
        return "HIGH"
    if max_overlap >= _MEDIUM_OVERLAP_THRESHOLD or max_run >= _MEDIUM_RUN_THRESHOLD:
        return "MEDIUM"
    return "LOW"


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def analyze_draft(draft_path: Path) -> None:
    draft_text = draft_path.read_text(encoding="utf-8")
    draft_tokens = tokenize(draft_text)

    sample_files = list(PARSED_DIR.glob("*.md"))
    if not sample_files:
        log.warning(
            "No sample files found in %s — comparison skipped.", PARSED_DIR
        )
        _print_report(
            risk="UNKNOWN",
            max_overlap=0.0,
            max_run=0,
            sample_count=0,
            files_with_signal=0,
            rapidfuzz_max=None,
        )
        return

    max_overlap = 0.0
    max_run = 0
    files_with_signal = 0

    for sample_path in sample_files:
        try:
            sample_text = sample_path.read_text(encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            log.warning("Could not read sample file: %s", exc)
            continue

        sample_tokens = tokenize(sample_text)
        overlap = ngram_overlap(draft_tokens, sample_tokens, n=5)
        run = longest_common_token_run(draft_tokens, sample_tokens)

        if overlap >= _MEDIUM_OVERLAP_THRESHOLD or run >= _MEDIUM_RUN_THRESHOLD:
            files_with_signal += 1

        if overlap > max_overlap:
            max_overlap = overlap
        if run > max_run:
            max_run = run

    # Optional rapidfuzz similarity (token_set_ratio)
    rapidfuzz_max: Optional[float] = None
    try:
        from rapidfuzz import fuzz  # type: ignore[import]

        scores: list[float] = []
        for sample_path in sample_files:
            try:
                sample_text = sample_path.read_text(encoding="utf-8")
                scores.append(fuzz.token_set_ratio(draft_text, sample_text) / 100.0)
            except Exception:  # noqa: BLE001
                pass
        if scores:
            rapidfuzz_max = max(scores)
    except ImportError:
        pass  # rapidfuzz is optional

    risk = classify_risk(max_overlap, max_run)
    _print_report(
        risk=risk,
        max_overlap=max_overlap,
        max_run=max_run,
        sample_count=len(sample_files),
        files_with_signal=files_with_signal,
        rapidfuzz_max=rapidfuzz_max,
    )


# ---------------------------------------------------------------------------
# Output (never reveals matching text or sample filenames)
# ---------------------------------------------------------------------------

def _print_report(
    risk: str,
    max_overlap: float,
    max_run: int,
    sample_count: int,
    files_with_signal: int,
    rapidfuzz_max: Optional[float],
) -> None:
    sep = "=" * 60
    print(sep)
    print("ORIGINALITY CHECK REPORT")
    print(sep)
    print(f"Risk Level             : {risk}")
    print(f"Samples Compared       : {sample_count}")
    print(f"Max 5-gram Overlap     : {max_overlap:.2%}")
    print(f"Max Common Token Run   : {max_run} tokens")
    print(f"Files with signal      : {files_with_signal}")
    if rapidfuzz_max is not None:
        print(f"RapidFuzz Max Score    : {rapidfuzz_max:.2%}")
    print()

    if risk == "HIGH":
        print("Reasons (generic):")
        if max_overlap >= _HIGH_OVERLAP_THRESHOLD:
            print("  - High token n-gram overlap detected across one or more samples")
        if max_run >= _HIGH_RUN_THRESHOLD:
            print("  - Long verbatim token sequence detected")
        print()
        print("Suggested Actions:")
        print("  1. Review your draft for sections that closely mirror sample phrasing")
        print("  2. Rewrite flagged sections using only your own words and experiences")
        print("  3. Ensure all content reflects your genuine background")
        print("  4. Re-run this check after revisions")
    elif risk == "MEDIUM":
        print("Reasons (generic):")
        print("  - Moderate token-level overlap detected with one or more samples")
        print()
        print("Suggested Actions:")
        print("  1. Review your draft to confirm all content is original")
        print("  2. Vary sentence structure and vocabulary where possible")
        print("  3. Verify that shared phrases are standard academic conventions,")
        print("     not borrowed from samples")
    elif risk == "UNKNOWN":
        print("Could not compare — no sample files found.")
        print("Run parse_documents.py first to populate data/parsed-private/.")
    else:
        print("No significant similarity detected.")
        print("Your draft appears to be original at the token level.")

    print(sep)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Check a user draft essay for token-level similarity "
            "against the parsed sample corpus."
        )
    )
    parser.add_argument(
        "--draft",
        required=True,
        type=Path,
        metavar="FILE",
        help="Path to your draft essay (plain text or Markdown).",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    if not args.draft.exists():
        log.error("Draft file not found: %s", args.draft)
        sys.exit(1)

    analyze_draft(args.draft)


if __name__ == "__main__":
    main()
