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
    bbox         - Geographic bounding box: {north, south, east, west} in decimal degrees
                   Matches against the notification's GeoJSON geometry. Notifications with
                   no geometry (null) are passed through.
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

from shapely.geometry import Point, Polygon, shape

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
    geometry: dict | None = None
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
            s = str(value)
            if s.endswith('Z'):
                s = s[:-1] + '+00:00'
            return datetime.datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None
    LOGGER.warning(f"Unknown type_hint '{type_hint}' in property match; value not coerced")
    return None


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
        if not isinstance(operand, (list, tuple)):
            LOGGER.warning(f"Operator 'in' expects a list operand, got {type(operand).__name__!r}")
            return False
        return value in operand
    if operator == 'not_in':
        if not isinstance(operand, (list, tuple)):
            LOGGER.warning(f"Operator 'not_in' expects a list operand, got {type(operand).__name__!r}")
            return False
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
    LOGGER.warning(f"No recognised size operator in condition: {list(condition.keys())}")
    return False


def _match_bbox(condition: dict, geometry: dict | None) -> bool:
    """Evaluate a bbox condition against a GeoJSON geometry dict.

    Returns True (pass through) when geometry is None — no location info available.
    Unsupported geometry types also pass through (logged at DEBUG).
    """
    if geometry is None:
        return True  # pass through: no geometry to test against

    required = ('north', 'south', 'east', 'west')
    if not all(k in condition for k in required):
        LOGGER.warning(
            f"bbox condition missing fields; expected north/south/east/west, "
            f"got {list(condition.keys())}"
        )
        return False

    north = condition['north']
    south = condition['south']
    east = condition['east']
    west = condition['west']

    bbox_polygon = Polygon([
        (west, south), (east, south), (east, north), (west, north), (west, south),
    ])

    geom_type = geometry.get('type')
    coordinates = geometry.get('coordinates')

    try:
        if geom_type == 'Point':
            return Point(coordinates[0], coordinates[1]).within(bbox_polygon)
        if geom_type in ('Polygon', 'MultiPolygon'):
            return shape(geometry).intersects(bbox_polygon)
    except Exception as exc:
        LOGGER.warning(f"bbox geometry evaluation failed ({geom_type}): {exc}")
        return True  # fail open

    LOGGER.debug(f"Unsupported geometry type '{geom_type}' in bbox match; passing through")
    return True


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
        if not isinstance(match['not'], dict):
            LOGGER.warning(f"'not' combinator expects a dict condition, got {type(match['not']).__name__!r}")
            return False
        return not _evaluate_match(match['not'], ctx)

    # size (dedicated byte-unit operators)
    if 'size' in match:
        return _match_size(match['size'], ctx.size)

    # bbox (geographic bounding box against GeoJSON geometry)
    if 'bbox' in match:
        return _match_bbox(match['bbox'], ctx.geometry)

    # property (dynamic WIS2 notification property)
    if 'property' in match:
        prop_name = match['property']
        type_hint = match.get('type', 'string')
        raw_value = ctx.properties.get(prop_name)
        value = _coerce(raw_value, type_hint)
        for op in match:
            if op in _KNOWN_OPERATORS:
                operand = match[op]
                if op == 'between':
                    if isinstance(operand, (list, tuple)) and type_hint in ('integer', 'number', 'datetime'):
                        operand = [_coerce(b, type_hint) for b in operand]
                elif op not in ('in', 'not_in', 'exists') and type_hint in ('integer', 'number', 'datetime'):
                    operand = _coerce(operand, type_hint)
                return _apply_operator(value, op, operand)
        LOGGER.warning(f"Property match '{prop_name}' has no recognised operator")
        return False

    # simple field matches (media_type, centre_id, data_id, metadata_id, topic, href)
    for key in match:
        if key in _SIMPLE_FIELDS:
            condition = match[key]
            value = getattr(ctx, key, None)
            for op in condition:
                if op in _KNOWN_OPERATORS:
                    return _apply_operator(value, op, condition[op])
            LOGGER.warning(f"Field match '{key}' has no recognised operator in {condition}")
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
            LOGGER.warning(f"Rule '{rule_id}' raised an error and was skipped (fail-open): {exc}", exc_info=True)
            continue

        if not matched:
            continue

        action = rule.get('action', 'continue')
        reason = rule.get('reason') or rule_id

        if action == 'accept':
            return 'accept', reason
        if action == 'reject':
            LOGGER.error(
                f"Rule '{rule_id}' matched (action=reject), skipping notification "
                f"[topic={ctx.topic}, media_type={ctx.media_type}, "
                f"size={ctx.size}, centre_id={ctx.centre_id}, "
                f"data_id={ctx.data_id}, href={ctx.href}]"
            )
            return 'reject', reason
        # action == 'continue': rule matched but we keep going
        LOGGER.debug(f"Rule '{rule_id}' matched (action=continue), proceeding to next rule")

    # No rule produced a definitive accept/reject — default is accept
    LOGGER.debug("No filter rule produced a definitive outcome; defaulting to accept")
    return 'accept', None
