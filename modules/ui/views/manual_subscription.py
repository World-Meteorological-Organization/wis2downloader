import json
import re
from nicegui import ui

from i18n import t
from views.shared import confirm_subscribe, _collect_credentials

# Valid WIS2 topic: (cache|origin)/a/wis2/{centre-id or +}/data[/segments][/#]
# - centre-id: alphanumerics + hyphens/underscores, or + wildcard
# - further segments: alphanumerics + hyphens/underscores, or + wildcard
# - # only as trailing /#, never mid-topic
_TOPIC_RE = re.compile(
    r'^(cache|origin)/a/wis2/'         # required prefix
    r'([a-zA-Z0-9_-]+|\+)/'            # centre-id or + wildcard
    r'data'                             # literal "data" (5th level)
    r'(/([a-zA-Z0-9_-]+|\+))*'         # zero or more /segment or /+
    r'(/#)?$'                           # optional trailing /#
)

_REQUIRED_RULE_FIELDS: dict[str, type | tuple] = {
    'id':     str,
    'order':  (int, float),
    'match':  dict,
    'action': str,
}
_VALID_ACTIONS = frozenset({'accept', 'reject', 'continue'})


def _validate_topic(v: str) -> str | None:
    if not v or not v.strip():
        return t('manual.val.topic_required')
    if not _TOPIC_RE.match(v.strip()):
        return t('manual.val.topic_format')
    return None


def _validate_target(v: str) -> str | None:
    if not v:
        return None  # optional — defaults to ./
    if '..' in v.split('/'):
        return t('manual.val.path_traversal')
    if v.startswith('/'):
        return t('manual.val.path_absolute')
    return None


def _validate_filter(v: str) -> str | None:
    v = (v or '').strip()
    if not v or v == '{}':
        return None  # empty = use the built-in default filter

    try:
        parsed = json.loads(v)
    except json.JSONDecodeError as e:
        return t('manual.val.json_invalid', msg=e.msg, lineno=e.lineno, colno=e.colno)

    if not isinstance(parsed, dict):
        return t('manual.val.not_object')
    if 'rules' not in parsed:
        return t('manual.val.missing_rules')
    rules = parsed['rules']
    if not isinstance(rules, list):
        return t('manual.val.rules_not_array')

    for i, rule in enumerate(rules):
        if not isinstance(rule, dict):
            return t('manual.val.rule_not_object', i=i)
        for field, expected_type in _REQUIRED_RULE_FIELDS.items():
            if field not in rule:
                return t('manual.val.rule_missing_field', i=i, field=field)
            if not isinstance(rule[field], expected_type):
                type_name = (
                    expected_type.__name__
                    if isinstance(expected_type, type)
                    else 'number'
                )
                return t('manual.val.rule_wrong_type', i=i, field=field, type_name=type_name)
        if rule['action'] not in _VALID_ACTIONS:
            return t('manual.val.rule_bad_action', i=i)

    return None


def render(container):
    with container:
        ui.label(t('manual.title')).classes("page-title")

        with ui.card().classes("manual-sub-card"):
            with ui.card_section():
                ui.label(t('manual.description')).classes("text-body2 text-grey-7")

                topic_input = ui.input(
                    label=t('manual.topic_label'),
                    placeholder=t('manual.topic_hint'),
                    validation=_validate_topic,
                ).classes("directory-input")

                target_input = ui.input(
                    label=t('manual.target_label'),
                    placeholder=t('sidebar.save_directory_hint'),
                    validation=_validate_target,
                ).classes("directory-input")

                filter_area = ui.textarea(
                    label=t('manual.filter_label'),
                    placeholder=t('manual.filter_hint'),
                    validation=_validate_filter,
                ).classes("directory-input filter-textarea")

                ui.separator()

                ui.label(t('sidebar.auth')).classes("sidebar-section-title")
                auth_type = ui.radio(
                    {
                        'none': t('sidebar.auth_none'),
                        'basic': t('sidebar.auth_basic'),
                        'bearer': t('sidebar.auth_bearer'),
                    },
                    value='none',
                ).props('inline')

                _req = lambda v: t('validation.auth_credentials_required') if not (v or '').strip() else None

                with ui.column().bind_visibility_from(
                    auth_type, 'value', backward=lambda v: v == 'basic'
                ):
                    username_input = ui.input(
                        label=t('sidebar.auth_username'),
                        validation=_req,
                    ).classes("directory-input")
                    password_input = ui.input(
                        label=t('sidebar.auth_password'),
                        password=True,
                        password_toggle_button=True,
                        validation=_req,
                    ).classes("directory-input")

                with ui.column().bind_visibility_from(
                    auth_type, 'value', backward=lambda v: v == 'bearer'
                ):
                    token_input = ui.input(
                        label=t('sidebar.auth_token'),
                        password=True,
                        password_toggle_button=True,
                        validation=_req,
                    ).classes("directory-input")

                def on_subscribe():
                    # Force validation on all fields (catches fields never touched)
                    topic_input.validate()
                    target_input.validate()
                    filter_area.validate()

                    if auth_type.value == 'basic':
                        username_input.validate()
                        password_input.validate()
                    elif auth_type.value == 'bearer':
                        token_input.validate()

                    if any(f.error for f in [topic_input, target_input, filter_area]):
                        ui.notify(t('validation.fix_errors'), type='warning')
                        return

                    credentials = _collect_credentials(
                        None, auth_type, username_input, password_input, token_input
                    )
                    if credentials is False:
                        return

                    topic = topic_input.value.strip()
                    raw = (filter_area.value or '').strip()
                    filters = json.loads(raw) if raw and raw != '{}' else {}
                    confirm_subscribe({topic: filters}, target_input.value, credentials)

                ui.button(t('btn.subscribe'), icon="check_circle").classes("subscribe-btn").on(
                    'click', on_subscribe,
                )
