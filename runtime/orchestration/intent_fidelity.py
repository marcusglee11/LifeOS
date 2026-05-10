from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

VALID_BLOCKING_STRENGTHS = {"blocking", "warning", "requires_conductor_review"}
VALID_BRIEF_TYPES = {
    "worker_prompt",
    "dispatch_packet",
    "build_packet",
    "implementation_plan",
    "pr_body",
    "issue_comment",
    "closure_packet",
    "other",
}
DEFAULT_LEXICON_PATH = Path(__file__).resolve().parents[1] / "data" / "intent_lexicon_v1.json"
NON_DESTRUCTIVE_SOURCE_TERMS = ("add", "improve", "keep", "intact")
NON_DESTRUCTIVE_INVERSION_TERMS = (
    "gut",
    "rewrite",
    "replace",
    "from scratch",
    "start from scratch",
    "start over",
)


@dataclass
class IntentSpan:
    intent_class: str
    phrase: str
    source_id: str
    line_or_offset: str
    surrounding_context: str
    blocking_strength: str
    guard_triggered: Optional[str] = None


@dataclass
class IntentLexicon:
    data: dict

    @classmethod
    def load(cls, path: str | Path) -> "IntentLexicon":
        """Load and validate the lexicon JSON file."""
        lexicon_path = Path(path)
        data = json.loads(lexicon_path.read_text(encoding="utf-8"))
        if data.get("schema_version") != "intent_lexicon_v1":
            raise ValueError("lexicon schema_version must be intent_lexicon_v1")
        if not data.get("version"):
            raise ValueError("lexicon version is required")
        intent_classes = data.get("intent_classes")
        if not isinstance(intent_classes, list) or not intent_classes:
            raise ValueError("lexicon intent_classes must be a non-empty list")

        required = {
            "class",
            "phrases",
            "default_blocking",
            "inversion_terms",
            "negation_guards",
        }
        seen: set[str] = set()
        for item in intent_classes:
            missing = required - set(item)
            if missing:
                raise ValueError(f"intent class missing required fields: {sorted(missing)}")
            if item["class"] in seen:
                raise ValueError(f"duplicate intent class: {item['class']}")
            seen.add(item["class"])
            if item["default_blocking"] not in VALID_BLOCKING_STRENGTHS:
                raise ValueError(f"invalid default_blocking: {item['default_blocking']}")
            for list_field in ("phrases", "inversion_terms", "negation_guards"):
                if not isinstance(item[list_field], list):
                    raise ValueError(f"{item['class']}.{list_field} must be a list")
        return cls(data=data)

    def get_class(self, class_name: str) -> dict | None:
        """Get an intent class definition by name."""
        for item in self.data.get("intent_classes", []):
            if item.get("class") == class_name:
                return item
        return None


def load_lexicon(path: str | Path) -> IntentLexicon:
    """Convenience wrapper for IntentLexicon.load()."""
    return IntentLexicon.load(path)


def _phrase_pattern(phrase: str) -> re.Pattern[str]:
    escaped_parts = [re.escape(part) for part in phrase.split()]
    body = r"\s+".join(escaped_parts)
    return re.compile(rf"(?<![\w-]){body}(?![\w-])", re.IGNORECASE)


def _line_or_offset(text: str, start: int) -> str:
    line = text.count("\n", 0, start) + 1
    previous_newline = text.rfind("\n", 0, start)
    column = start + 1 if previous_newline == -1 else start - previous_newline
    return f"line {line}, offset {column}"


def _context(text: str, start: int, end: int, radius: int = 60) -> str:
    return text[max(0, start - radius) : min(len(text), end + radius)].strip()


def _indicator_before(text: str, start: int, indicators: tuple[str, ...], window: int) -> bool:
    prefix = text[max(0, start - window) : start].lower()
    prefix = re.sub(r"\s+", " ", prefix)
    for indicator in indicators:
        pattern = rf"(^|[\s,.;:!?]){re.escape(indicator)}([\s,.;:!?]|$)"
        if re.search(pattern, prefix):
            return True
    return False


def _guard_phrase_before_match(text: str, start: int, end: int, guard_phrases: list[str]) -> bool:
    window = text[max(0, start - 40) : end].lower()
    normalized = re.sub(r"\s+", " ", window)
    return any(guard.lower() in normalized for guard in guard_phrases)


def _inside_quote(text: str, position: int) -> bool:
    active_quote: str | None = None
    escaped = False
    for index, char in enumerate(text[:position]):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char not in {"'", '"'}:
            continue
        if char == "'" and 0 < index < len(text) - 1:
            if text[index - 1].isalnum() and text[index + 1].isalnum():
                continue
        if active_quote == char:
            active_quote = None
        elif active_quote is None:
            active_quote = char
    return active_quote is not None


def _triggered_guard(
    text: str,
    start: int,
    end: int,
    class_def: dict,
) -> str | None:
    if _guard_phrase_before_match(text, start, end, class_def.get("negation_guards", [])):
        return "negation"
    if _indicator_before(
        text,
        start,
        ("not", "no", "never", "don't", "do not", "does not", "did not", "won't"),
        24,
    ):
        return "negation"
    if _indicator_before(
        text,
        start,
        (
            "previously",
            "before",
            "used to",
            "was",
            "were",
            "had",
            "past",
            "originally",
            "earlier",
            "once",
            "former",
        ),
        32,
    ):
        return "historical"
    if _indicator_before(
        text,
        start,
        (
            "if",
            "what if",
            "suppose",
            "imagine",
            "might",
            "could",
            "would",
            "maybe",
            "perhaps",
            "consider",
            "option",
        ),
        32,
    ):
        return "hypothetical"
    if _inside_quote(text, start):
        return "third_party_quote"
    return None


def extract_intents(text: str, source_id: str, lexicon: IntentLexicon) -> list[IntentSpan]:
    """
    Extract intent spans from text using the given lexicon.

    Guarded matches are suppressed from output. Same text and lexicon version produce
    identical span lists.
    """
    if not text:
        return []

    collected: list[tuple[int, str, str, IntentSpan]] = []
    for class_def in lexicon.data.get("intent_classes", []):
        intent_class = class_def["class"]
        for phrase in class_def["phrases"]:
            for match in _phrase_pattern(phrase).finditer(text):
                guard = _triggered_guard(text, match.start(), match.end(), class_def)
                if guard:
                    continue
                span = IntentSpan(
                    intent_class=intent_class,
                    phrase=phrase,
                    source_id=source_id,
                    line_or_offset=_line_or_offset(text, match.start()),
                    surrounding_context=_context(text, match.start(), match.end()),
                    blocking_strength=class_def["default_blocking"],
                    guard_triggered=None,
                )
                collected.append((match.start(), intent_class, phrase, span))

    collected.sort(key=lambda item: (item[0], item[1], item[2]))
    spans = [item[3] for item in collected]
    absence_exists = any(span.intent_class == "absence" for span in spans)
    if absence_exists:
        for span in spans:
            if span.intent_class == "softening_inversion":
                span.blocking_strength = "blocking"
    return spans


def hash_text(text: str) -> str:
    """SHA-256 hash of text content."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def determinism_check(text: str, lexicon: IntentLexicon) -> bool:
    """Run extraction twice on same input and verify results match."""
    first = [asdict(span) for span in extract_intents(text, "determinism", lexicon)]
    second = [asdict(span) for span in extract_intents(text, "determinism", lexicon)]
    return first == second


@dataclass
class SourceManifest:
    schema_version: str
    work_item_id: str
    lexicon_version: str
    created_at: str
    created_by: str
    source_discovery: dict
    sources: list[dict]
    missing_sources: list[dict]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validate_sha256(value: str, field_name: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError(f"{field_name} must be a SHA-256 hex string")


def _intent_to_dict(intent: IntentSpan | dict) -> dict:
    if isinstance(intent, IntentSpan):
        return asdict(intent)
    return {
        "intent_class": intent["intent_class"],
        "phrase": intent["phrase"],
        "source_id": intent.get("source_id"),
        "line_or_offset": intent["line_or_offset"],
        "surrounding_context": intent["surrounding_context"],
        "blocking_strength": intent["blocking_strength"],
        "guard_triggered": intent.get("guard_triggered"),
    }


def _normalise_source_discovery(source_discovery: dict, created_at: str) -> dict:
    return {
        "mode": source_discovery.get("mode", "local_file"),
        "commands_or_uris": list(source_discovery.get("commands_or_uris", [])),
        "command_output_hashes_sha256": list(
            source_discovery.get("command_output_hashes_sha256", [])
        ),
        "cutoff_timestamp": source_discovery.get("cutoff_timestamp", created_at),
        "completeness_claimed_by": source_discovery.get("completeness_claimed_by", "tool"),
    }


def build_source_manifest(
    work_item_id: str,
    lexicon_version: str,
    source_discovery: dict,
    sources: list[dict],
    missing_sources: list[dict] | None = None,
    created_by: str = "tool",
) -> SourceManifest:
    """
    Build a source manifest from discovered sources and extracted intents.

    Source dictionaries may include private `content` or `text` keys for local extraction.
    Those bytes are hashed and retained only in-memory as `_content`; serialization strips
    private keys.
    """
    created_at = _now_iso()
    lexicon = load_lexicon(DEFAULT_LEXICON_PATH)
    normalised_sources: list[dict] = []

    for index, source in enumerate(sources, start=1):
        source_id = source.get("source_id", f"source-{index}")
        content = str(source.get("content", source.get("text", "")))
        content_hash = source.get("content_hash_sha256") or hash_text(content)
        _validate_sha256(content_hash, "content_hash_sha256")

        source_of_source_hash = source.get("source_of_source_hash_sha256")
        if source_of_source_hash is not None:
            _validate_sha256(source_of_source_hash, "source_of_source_hash_sha256")
        if source.get("retrieval_method") == "primary" and source_of_source_hash is not None:
            raise ValueError("source_of_source_hash_sha256 must be null for primary sources")

        extracted = source.get("extracted_intents")
        if extracted is None and content:
            extracted = extract_intents(content, source_id, lexicon)
        extracted_dicts = [_intent_to_dict(intent) for intent in extracted or []]

        normalised = {
            "source_id": source_id,
            "source_type": source.get("source_type", "local_file"),
            "uri": source.get("uri", source_id),
            "retrieved_at": source.get("retrieved_at", created_at),
            "retrieval_method": source.get("retrieval_method", "local_file"),
            "content_hash_sha256": content_hash,
            "source_of_source_hash_sha256": source_of_source_hash,
            "authority_tier": source.get("authority_tier", "current_ceo_instruction"),
            "extracted_intents": extracted_dicts,
        }
        if content:
            normalised["_content"] = content
        normalised_sources.append(normalised)

    return SourceManifest(
        schema_version="intent_source_manifest.v1",
        work_item_id=work_item_id,
        lexicon_version=lexicon_version,
        created_at=created_at,
        created_by=created_by,
        source_discovery=_normalise_source_discovery(source_discovery, created_at),
        sources=normalised_sources,
        missing_sources=list(missing_sources or []),
    )


def manifest_to_dict(manifest: SourceManifest) -> dict:
    """Convert manifest to serializable dict."""
    payload = asdict(manifest)
    payload["sources"] = [
        {key: value for key, value in source.items() if not key.startswith("_")}
        for source in payload["sources"]
    ]
    return payload


def validate_manifest_completeness(manifest: SourceManifest) -> tuple[bool, list[str]]:
    """
    Validate source completeness.
    Returns (is_complete, issues_list).
    Fails closed if any missing_source has disposition "fail_closed".
    """
    issues: list[str] = []
    for missing in manifest.missing_sources:
        if missing.get("disposition") == "fail_closed":
            expected = missing.get("expected_source", "unknown source")
            reason = missing.get("reason_missing", "missing")
            issues.append(f"missing required source: {expected} ({reason})")
    return not issues, issues


@dataclass
class FidelityCheck:
    """Result of a single check within the fidelity report."""

    status: str
    details: list[str] = field(default_factory=list)


@dataclass
class FidelityReport:
    schema_version: str
    work_item_id: str
    brief_type: str
    brief_hash_sha256: str
    source_manifest_uri: str
    decision: str
    checks: dict
    false_positive_fixtures_passed: int = 0


def _span_from_dict(payload: dict) -> IntentSpan:
    return IntentSpan(
        intent_class=payload["intent_class"],
        phrase=payload["phrase"],
        source_id=payload.get("source_id") or "",
        line_or_offset=payload["line_or_offset"],
        surrounding_context=payload["surrounding_context"],
        blocking_strength=payload["blocking_strength"],
        guard_triggered=payload.get("guard_triggered"),
    )


def _source_intents(manifest: SourceManifest) -> list[IntentSpan]:
    spans: list[IntentSpan] = []
    for source in manifest.sources:
        for intent in source.get("extracted_intents", []):
            spans.append(_span_from_dict(intent))
    return spans


def _source_text(manifest: SourceManifest) -> str:
    return "\n".join(source.get("_content", "") for source in manifest.sources)


def _contains_any(text: str, terms: list[str] | tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in terms)


def _inversion_term_spans(
    brief_text: str,
    source_intents: list[IntentSpan],
    lexicon: IntentLexicon,
) -> list[IntentSpan]:
    terms: set[str] = set(NON_DESTRUCTIVE_INVERSION_TERMS)
    for source_intent in source_intents:
        class_def = lexicon.get_class(source_intent.intent_class)
        if class_def:
            terms.update(class_def.get("inversion_terms", []))

    spans: list[IntentSpan] = []
    for term in sorted(terms):
        if term and term in brief_text.lower():
            start = brief_text.lower().find(term)
            spans.append(
                IntentSpan(
                    intent_class="inversion_term",
                    phrase=term,
                    source_id="brief",
                    line_or_offset=_line_or_offset(brief_text, start),
                    surrounding_context=_context(brief_text, start, start + len(term)),
                    blocking_strength="requires_conductor_review",
                )
            )
    return spans


def check_inversion(
    source_intents: list[IntentSpan],
    brief_intents: list[IntentSpan],
    lexicon: IntentLexicon,
) -> FidelityCheck:
    """
    Check if the brief inverts any source intents.

    If source says remove/delete/hide/start over, polish/cleanup/iteration framing is a
    blocking inversion unless the brief explicitly preserves the absence requirement.
    """
    details: list[str] = []
    brief_classes = {span.intent_class for span in brief_intents}
    brief_terms = " ".join(
        f"{span.phrase} {span.surrounding_context}" for span in brief_intents
    ).lower()

    for source_intent in source_intents:
        if source_intent.blocking_strength != "blocking":
            continue
        class_def = lexicon.get_class(source_intent.intent_class)
        if not class_def:
            continue
        inversion_terms = class_def.get("inversion_terms", [])
        inverted_terms = [term for term in inversion_terms if term in brief_terms]
        if not inverted_terms:
            continue
        if source_intent.intent_class == "absence" and "absence" in brief_classes:
            continue
        details.append(
            "blocking inversion: "
            f"{source_intent.intent_class} source intent '{source_intent.phrase}' "
            f"reframed by {sorted(inverted_terms)}"
        )

    return FidelityCheck(status="fail" if details else "pass", details=details)


def _verbatim_preservation_check(
    source_intents: list[IntentSpan],
    brief_text: str,
    brief_intents: list[IntentSpan],
) -> FidelityCheck:
    brief_lower = brief_text.lower()
    brief_classes = {intent.intent_class for intent in brief_intents}
    details: list[str] = []
    preserved = 0
    relevant = [
        span for span in source_intents if span.blocking_strength in VALID_BLOCKING_STRENGTHS
    ]

    for source_intent in relevant:
        phrase_preserved = source_intent.phrase.lower() in brief_lower
        class_mapped = source_intent.intent_class in brief_classes
        if phrase_preserved or class_mapped:
            preserved += 1
            continue
        details.append(
            f"missing mapped source intent: {source_intent.intent_class}:{source_intent.phrase}"
        )

    if not details:
        return FidelityCheck(
            status="pass",
            details=[f"{preserved}/{len(relevant)} source intents preserved or mapped"],
        )
    if any(span.blocking_strength == "blocking" for span in relevant):
        return FidelityCheck(status="requires_conductor_review", details=details)
    return FidelityCheck(status="warn", details=details)


def _hedge_or_softening_check(
    source_intents: list[IntentSpan],
    brief_intents: list[IntentSpan],
) -> FidelityCheck:
    softening = [
        span.phrase for span in brief_intents if span.intent_class == "softening_inversion"
    ]
    if not softening:
        return FidelityCheck(status="pass", details=[])
    has_blocking_source = any(span.blocking_strength == "blocking" for span in source_intents)
    status = "warn" if not has_blocking_source else "fail"
    return FidelityCheck(status=status, details=[f"softening terms present: {sorted(softening)}"])


def _contradiction_check(brief_text: str) -> FidelityCheck:
    lowered = brief_text.lower()
    if "do not remove" in lowered and re.search(r"(?<!do not )\bremove\b", lowered):
        return FidelityCheck(
            status="requires_ceo_clarification",
            details=["brief contains both removal and do-not-remove language"],
        )
    return FidelityCheck(status="pass", details=[])


def _false_positive_fixture_count(lexicon: IntentLexicon) -> int:
    samples = {
        "negation": "Do not remove the export button.",
        "historical": "We previously remove the staging banner.",
        "hypothetical": "If we remove the analytics tab, would it break?",
        "third_party_quote": 'The reviewer said "they should delete this panel".',
    }
    count = 0
    for name, sample in samples.items():
        spans = extract_intents(sample, name, lexicon)
        if not any(span.intent_class == "absence" for span in spans):
            count += 1
    return count


def _decision_from_checks(checks: dict[str, FidelityCheck]) -> str:
    statuses = {check.status for check in checks.values()}
    if "fail" in statuses:
        return "fail_closed"
    if "requires_ceo_clarification" in statuses:
        return "requires_ceo_clarification"
    if "requires_conductor_review" in statuses:
        return "requires_conductor_review"
    if "warn" in statuses:
        return "warning_only"
    return "pass"


def _non_destructive_boundary_check(
    source_text_value: str,
    brief_text: str,
    source_intents: list[IntentSpan],
) -> FidelityCheck:
    if source_intents:
        return FidelityCheck(status="pass", details=[])
    if not _contains_any(source_text_value, NON_DESTRUCTIVE_SOURCE_TERMS):
        return FidelityCheck(status="pass", details=[])
    if _contains_any(brief_text, NON_DESTRUCTIVE_INVERSION_TERMS):
        return FidelityCheck(
            status="fail",
            details=["non-destructive source reframed as gut/rewrite/from-scratch work"],
        )
    return FidelityCheck(status="pass", details=[])


def check_fidelity(
    brief_text: str,
    brief_type: str,
    source_manifest: SourceManifest,
    lexicon: IntentLexicon,
) -> FidelityReport:
    """
    Compare a brief against source intents.

    This is a deterministic dry-run report. It does not grant implementation authority.
    """
    if brief_type not in VALID_BRIEF_TYPES:
        raise ValueError(f"invalid brief_type: {brief_type}")

    source_intents = _source_intents(source_manifest)
    brief_intents = extract_intents(brief_text, "brief", lexicon)
    brief_intents_for_inversion = brief_intents + _inversion_term_spans(
        brief_text,
        source_intents,
        lexicon,
    )

    coverage_ok, coverage_issues = validate_manifest_completeness(source_manifest)
    checks: dict[str, FidelityCheck] = {
        "source_coverage": FidelityCheck(
            status="pass" if coverage_ok else "fail",
            details=coverage_issues,
        ),
        "verbatim_preservation": _verbatim_preservation_check(
            source_intents,
            brief_text,
            brief_intents,
        ),
        "intent_inversion": check_inversion(
            source_intents,
            brief_intents_for_inversion,
            lexicon,
        ),
        "hedge_or_softening": _hedge_or_softening_check(source_intents, brief_intents),
        "contradiction_detection": _contradiction_check(brief_text),
        "determinism_check": FidelityCheck(
            status="pass" if determinism_check(brief_text, lexicon) else "fail",
            details=[],
        ),
        "non_destructive_boundary": _non_destructive_boundary_check(
            _source_text(source_manifest),
            brief_text,
            source_intents,
        ),
    }
    decision = _decision_from_checks(checks)
    return FidelityReport(
        schema_version="intent_fidelity_report.v1",
        work_item_id=source_manifest.work_item_id,
        brief_type=brief_type,
        brief_hash_sha256=hash_text(brief_text),
        source_manifest_uri="in_memory",
        decision=decision,
        checks=checks,
        false_positive_fixtures_passed=_false_positive_fixture_count(lexicon),
    )


def fidelity_report_to_dict(report: FidelityReport) -> dict:
    payload = asdict(report)
    payload["checks"] = {
        name: asdict(check) if isinstance(check, FidelityCheck) else check
        for name, check in report.checks.items()
    }
    return payload
