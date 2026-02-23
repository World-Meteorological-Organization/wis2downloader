"""Rule-based filter engine for WIS2 download decisions.

Filter format (new hierarchical model):
    {
        "name": "my-filter",
        "rules": [
            {
                "id": "reject-large",
                "order": 1,
                "match": {"size": {"gt_bytes": 104857600}},
                "action": "reject",
                "reason": "File exceeds 100MB"
            },
            {
                "id": "accept-bufr",
                "order": 2,
                "match": {"media_type": {"equals": "application/bufr"}},
                "action": "accept"
            },
            {
                "id": "default",
                "order": 999,
                "match": {"always": true},
                "action": "reject"
            }
        ]
    }

Match fields:
    media_type   - MIME type of downloaded file (available post-download only)
    size         - File size in bytes (gt_bytes/gte_bytes/lt_bytes/lte_bytes/between_bytes)
    centre_id    - WIS2 centre identifier (position 3 in topic, e.g. "de-dwd")
    data_id      - From notification properties.data_id
    metadata_id  - From notification properties.metadata_id
    topic        - Full MQTT topic string
    href         - Download URL
    property     - Dynamic WIS2 notification property (requires "type" field)
    always       - Always/never matches (for default rules)

Operators (for simple fields and property):
    equals, not_equals, in, not_in, pattern (glob), regex
    gt, gte, lt, lte, between
    exists (bool: check if field is present/non-null)

Combinators:
    all  - All sub-conditions must match (AND)
    any  - Any sub-condition must match (OR)
    not  - Sub-condition must NOT match

Actions:
    accept   - Accept the notification (stop rule evaluation)
    reject   - Reject the notification (stop rule evaluation)
    continue - Rule matched but continue to the next rule

Pre-download vs post-download:
    Rules that reference media_type or size (actual bytes) can only be
    evaluated after the file is downloaded. When these fields are None in
    the MatchContext, any operator other than `exists: false` returns False,
    so rules depending on them naturally don't fire pre-download.
"""

import datetime
import fnmatch
import re
from dataclasses import dataclass, field

from .logging import setup_logging

LOGGER = setup_logging(__name__)

_KNOWN_OPERATORS = frozenset({
    'equals', 'not_equals', 'in', 'not_in', 'pattern', 'regex',
    'gt', 'gte', 'lt', 'lte', 'between', 'exists',
})

_SIMPLE_FIELDS = frozenset({
    'media_type', 'centre_id', 'data_id', 'metadata_id', 'topic', 'href',
})


@dataclass
class MatchContext:
    """All matchable values for filter evaluation.

    Populate with whatever is known at the point of evaluation.
    Fields that are None will cause operator checks to return False
    (except for `exists: false`), so rules requiring unknown fields
    simply do not fire.
    """
    topic: str | None = None
    centre_id: str | None = None
    data_id: str | None = None
    metadata_id: str | None = None
    href: str | None = None
    media_type: str | None = None
    size: int | None = None
    properties: dict = field(default_factory=dict)


def _coerce(value, type_hint: str):
    """Coerce value to the given type for comparison. Returns None on failure."""
    if value is None:
        return None
    try:
        if type_hint == 'string':
            return str(value)
        if type_hint == 'integer':
            return int(float(str(value)))
        if type_hint == 'number':
            return float(value)
        if type_hint == 'boolean':
            if isinstance(value, bool):
                return value
            return str(value).lower() in ('true', '1', 'yes')
        if type_hint == 'datetime':
            if isinstance(value, datetime.datetime):
                return value
            return datetime.datetime.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None
    return value


def _apply_operator(value, operator: str, operand) -> bool:
    """Apply a single operator. Returns False when value is None (except 'exists')."""
    if operator == 'exists':
        return (value is not None) == bool(operand)
    if value is None:
        return False
    if operator == 'equals':
        return value == operand
    if operator == 'not_equals':
        return value != operand
    if operator == 'in':
        return value in operand
    if operator == 'not_in':
        return value not in operand
    if operator == 'pattern':
        return fnmatch.fnmatch(str(value), str(operand))
    if operator == 'regex':
        return bool(re.search(str(operand), str(value)))
    if operator == 'gt':
        return value > operand
    if operator == 'gte':
        return value >= operand
    if operator == 'lt':
        return value < operand
    if operator == 'lte':
        return value <= operand
    if operator == 'between':
        return operand[0] <= value <= operand[1]
    return False


def _match_size(condition: dict, size: int | None) -> bool:
    """Evaluate size-specific byte operators against a size value."""
    if size is None:
        if 'exists' in condition:
            return not bool(condition['exists'])
        return False
    if 'gt_bytes' in condition:
        return size > condition['gt_bytes']
    if 'gte_bytes' in condition:
        return size >= condition['gte_bytes']
    if 'lt_bytes' in condition:
        return size < condition['lt_bytes']
    if 'lte_bytes' in condition:
        return size <= condition['lte_bytes']
    if 'between_bytes' in condition:
        low, high = condition['between_bytes']
        return low <= size <= high
    if 'exists' in condition:
        return bool(condition['exists'])
    return False


def _evaluate_match(match: dict, ctx: MatchContext) -> bool:
    """Recursively evaluate a match condition against a MatchContext."""
    # always / never
    if 'always' in match:
        return bool(match['always'])

    # logical combinators
    if 'all' in match:
        return all(_evaluate_match(m, ctx) for m in match['all'])
    if 'any' in match:
        return any(_evaluate_match(m, ctx) for m in match['any'])
    if 'not' in match:
        return not _evaluate_match(match['not'], ctx)

    # size (dedicated byte-unit operators)
    if 'size' in match:
        return _match_size(match['size'], ctx.size)

    # property (dynamic WIS2 notification property)
    if 'property' in match:
        prop_name = match['property']
        type_hint = match.get('type', 'string')
        raw_value = ctx.properties.get(prop_name)
        value = _coerce(raw_value, type_hint)
        for op in _KNOWN_OPERATORS:
            if op in match:
                operand = match[op]
                if op not in ('in', 'not_in', 'exists', 'between') and type_hint in ('integer', 'number'):
                    operand = _coerce(operand, type_hint)
                return _apply_operator(value, op, operand)
        LOGGER.warning(f"Property match '{prop_name}' has no recognised operator")
        return False

    # simple field matches (media_type, centre_id, data_id, metadata_id, topic, href)
    for field_name in _SIMPLE_FIELDS:
        if field_name in match:
            condition = match[field_name]
            value = getattr(ctx, field_name, None)
            for op in _KNOWN_OPERATORS:
                if op in condition:
                    return _apply_operator(value, op, condition[op])
            LOGGER.warning(f"Field match '{field_name}' has no recognised operator in {condition}")
            return False

    LOGGER.warning(f"Unrecognised match condition keys: {list(match.keys())}")
    return False


def apply_filters(filters: dict, ctx: MatchContext) -> tuple[str, str | None]:
    """Evaluate filter rules against a context.

    Rules are evaluated in ascending `order`. The first rule that matches
    and has action 'accept' or 'reject' determines the outcome.
    A rule with action 'continue' logs a match and moves to the next rule.

    Returns:
        ('accept', reason | None) — notification should be downloaded
        ('reject', reason)       — notification should be skipped
    """
    if not filters:
        return 'accept', None

    rules = filters.get('rules', [])
    if not rules:
        return 'accept', None

    sorted_rules = sorted(rules, key=lambda r: r.get('order', 9999))

    for rule in sorted_rules:
        rule_id = rule.get('id', '?')
        match_cond = rule.get('match', {})
        try:
            matched = _evaluate_match(match_cond, ctx)
        except Exception as exc:
            LOGGER.warning(f"Error evaluating rule '{rule_id}': {exc}", exc_info=True)
            continue

        if not matched:
            continue

        action = rule.get('action', 'continue')
        reason = rule.get('reason') or rule_id

        if action == 'accept':
            return 'accept', reason
        if action == 'reject':
            return 'reject', reason
        # action == 'continue': rule matched but we keep going
        LOGGER.debug(f"Rule '{rule_id}' matched (action=continue), proceeding to next rule")

    # No rule produced a definitive accept/reject — default is accept
    return 'accept', None
