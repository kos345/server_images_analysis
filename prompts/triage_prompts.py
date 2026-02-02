"""
Registry for triage LLM prompts.

This is a *scaffold* (каркас) meant to standardize:
- where prompts live (prompts/triage/*.md)
- how they are loaded (by key)
- how request/response logging should be done (metadata + redaction)

Do not hardcode pipeline logic in prompts. Prompts define tasks + output formats.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Optional


PROMPTS_DIR = Path(__file__).parent / "triage"


@dataclass(frozen=True)
class PromptSpec:
    key: str
    filename: str
    description: str

    @property
    def path(self) -> Path:
        return PROMPTS_DIR / self.filename


PROMPT_SPECS: Dict[str, PromptSpec] = {
    "system_services": PromptSpec(
        key="system_services",
        filename="system_services.md",
        description="Summarize and flag nonstandard/suspicious services from system/services.txt",
    ),
    "cron": PromptSpec(
        key="cron",
        filename="cron.md",
        description="Summarize and flag suspicious scheduled tasks from system/cron.txt",
    ),
    "apt_summary": PromptSpec(
        key="apt_summary",
        filename="apt_summary.md",
        description="Summarize and flag suspicious/dual-use packages from system/apt.txt",
    ),
    "log_files_summary": PromptSpec(
        key="log_files_summary",
        filename="log_files_summary.md",
        description="Infer web stack / special software from logs/var.txt and logs/www.txt",
    ),
    "root_files_summary": PromptSpec(
        key="root_files_summary",
        filename="root_files_summary.md",
        description="List nonstandard/suspicious items in filesystem root from files/root_dir.txt",
    ),
    "history_summary": PromptSpec(
        key="history_summary",
        filename="history_summary.md",
        description="Summarize command history and highlight suspicious patterns",
    ),
    "files_wl": PromptSpec(
        key="files_wl",
        filename="files_wl.md",
        description="Filter IOC file list: keep/drop with reasons (for VT lookup etc.)",
    ),
    "home_files_summary": PromptSpec(
        key="home_files_summary",
        filename="home_files_summary.md",
        description="Summarize suspicious files/directories in user homes",
    ),
}


def list_prompt_keys() -> Iterable[str]:
    """Return available prompt keys."""
    return PROMPT_SPECS.keys()


def get_prompt_path(key: str) -> Path:
    """Return filesystem path for a prompt by key."""
    if key not in PROMPT_SPECS:
        raise KeyError(f"Unknown prompt key: {key}. Known keys: {sorted(PROMPT_SPECS)}")
    return PROMPT_SPECS[key].path


def load_prompt_text(key: str, encoding: str = "utf-8") -> str:
    """Load prompt markdown content from disk."""
    path = get_prompt_path(key)
    return path.read_text(encoding=encoding)


def render_prompt_text(key: str, variables: Optional[Dict[str, str]] = None) -> str:
    """
    Render prompt text with simple placeholder substitution.

    This is intentionally minimal to avoid mixing business logic into templating.
    If needed later, swap to Jinja2 safely (with strict undefined).
    """
    text = load_prompt_text(key)
    if not variables:
        return text
    # Simple, explicit substitution (only exact placeholders).
    for k, v in variables.items():
        text = text.replace(f"{{{{{k}}}}}", v)
    return text


def logging_rules() -> str:
    """
    Human-readable logging rules for LLM calls (for implementation).

    The codebase should implement these rules in the LLM caller wrapper.
    """
    return (
        "Log LLM calls to file with: run_id, node, prompt_key, model, timestamp, "
        "request_size, response_size, latency_ms, and success/error. "
        "Store prompt version/hash. Do NOT log secrets (API keys/tokens) and redact "
        "sensitive artifacts (private keys, full /etc/shadow hashes, tokens). "
        "Prefer storing full prompts + responses on disk in a run-scoped directory "
        "with access controls; otherwise store truncated excerpts."
    )

