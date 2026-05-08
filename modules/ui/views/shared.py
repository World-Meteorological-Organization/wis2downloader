import copy
import json
import re
import httpx
from nicegui import ui

from config import SUBSCRIPTION_MANAGER
from data import get_datasets_for_channel, merged_records
from i18n import t
from shared import setup_logging

_DATE_RE = re.compile(r'^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$')
_TIME_RE = re.compile(r'^([01]\d|2[0-3]):[0-5]\d$')

setup_logging()
LOGGER = setup_logging(__name__)

DEFAULT_ACCEPTED_MEDIA_TYPES = [
    'image/gif', 'image/jpeg', 'image/png', 'image/tiff',
    'application/pdf', 'application/postscript',
    'application/bufr', 'application/grib',
    'application/x-bufr', 'application/x-grib',
    'application/x-hdf', 'application/x-hdf5',
    'application/x-netcdf', 'application/x-netcdf4',
    'text/plain', 'text/html', 'text/xml',
    'text/csv', 'text/tab-separated-values',
    'application/octet-stream',
]


def clean_page(state, layout):
    layout.right_sidebar.value = False
    layout.right_sidebar.clear()
    state.selected_topics = []
    state.selected_dataset_ids = []


def _centre_id(dataset_id: str) -> str:
    parts = dataset_id.split(':')
    return parts[3] if len(parts) > 3 else ''


def _collect_credentials(auth_container, auth_type, username_input, password_input, token_input):
    """Return credentials dict, None (no auth), or False (validation error shown).
    Pass auth_container=None to skip the visibility check (e.g. manual subscription view)."""
    if auth_container is not None and not auth_container.visible:
        return None
    if auth_type is None or auth_type.value == 'none':
        return None
    if auth_type.value == 'basic':
        u = (username_input.value or '').strip()
        p = (password_input.value or '').strip()
        if not u or not p:
            ui.notify(t('validation.auth_credentials_required'), type='warning')
            return False
        return {'type': 'basic', 'username': u, 'password': p}
    if auth_type.value == 'bearer':
        tkn = (token_input.value or '').strip()
        if not tkn:
            ui.notify(t('validation.auth_credentials_required'), type='warning')
            return False
        return {'type': 'bearer', 'token': tkn}
    return None


_REQUIRED_RULE_FIELDS: dict[str, type | tuple] = {
    'id':     str,
    'order':  (int, float),
    'match':  dict,
    'action': str,
}
_VALID_ACTIONS = frozenset({'accept', 'reject', 'continue'})


def _validate_target(v: str) -> str | None:
    if not v:
        return None  # optional — defaults to ./
    if v.startswith('/') or (len(v) >= 2 and v[1] == ':'):
        return t('manual.val.path_absolute')
    if any(part == '..' for part in v.replace('\\', '/').split('/')):
        return t('manual.val.path_traversal')
    return None


def _validate_filter(v: str) -> str | None:
    v = (v or '').strip()
    if not v or v == '{}':
        return None

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


def _try_parse_filter(filter_cfg: dict) -> dict | None:
    """Try to extract UI-control values from a filter built by _build_filter.

    Returns a dict with keys:
        dataset_ids, media_types, north, south, east, west,
        start_date, end_date, start_time, end_time
    or None when the filter structure cannot be represented by the standard
    controls (e.g. custom property conditions).
    """
    if not filter_cfg:
        return {
            'dataset_ids': [],
            'media_types': [], 'north': None, 'south': None,
            'east': None, 'west': None,
            'start_date': None, 'end_date': None,
            'start_time': None, 'end_time': None,
        }

    rules = filter_cfg.get('rules')
    if not isinstance(rules, list) or len(rules) != 2:
        return None

    accept_rule = next((r for r in rules if r.get('action') == 'accept'), None)
    reject_rule = next((r for r in rules if r.get('action') == 'reject'), None)
    if not accept_rule or not reject_rule:
        return None
    if reject_rule.get('match') != {'always': True}:
        return None

    match = accept_rule.get('match', {})
    conditions = match.get('all') if isinstance(match.get('all'), list) else [match]

    result: dict = {
        'dataset_ids': [],
        'media_types': [], 'north': None, 'south': None,
        'east': None, 'west': None,
        'start_date': None, 'end_date': None,
        'start_time': None, 'end_time': None,
    }

    for cond in conditions:
        if not isinstance(cond, dict):
            return None

        if 'any' in cond:
            # media-type condition: {"any": [..., {"media_type": {"in": [...]}}]}
            for item in cond['any']:
                if isinstance(item, dict) and isinstance(item.get('media_type'), dict):
                    mt = item['media_type'].get('in')
                    if isinstance(mt, list):
                        result['media_types'] = mt
                        break
        elif 'bbox' in cond:
            bbox = cond['bbox']
            result.update({
                'north': bbox.get('north'), 'south': bbox.get('south'),
                'east': bbox.get('east'), 'west': bbox.get('west'),
            })
        elif cond.get('property') == 'pubtime' and cond.get('type') == 'datetime':
            between = cond.get('between', [])
            if len(between) == 2:
                for val, dk, tk in [
                    (between[0], 'start_date', 'start_time'),
                    (between[1], 'end_date',   'end_time'),
                ]:
                    if 'T' in val:
                        d, rest = val.split('T', 1)
                        result[dk] = d
                        result[tk] = rest[:5]
        elif 'metadata_id' in cond:
            ids = cond['metadata_id'].get('in')
            if isinstance(ids, list):
                result['dataset_ids'] = ids
        else:
            return None  # unrecognised condition → fall back to textarea

    return result


def _preview_credentials(credentials: dict) -> dict:
    """Return a display-safe copy of credentials with secrets redacted."""
    if credentials.get('type') == 'basic':
        return {'type': 'basic', 'username': credentials['username'], 'password': '***'}
    if credentials.get('type') == 'bearer':
        return {'type': 'bearer', 'token': '***'}
    return credentials


def _build_filter(dataset_ids: list, media_type_select,
                  north, south, east, west,
                  start_date, end_date, start_time, end_time,
                  custom_inputs: dict, custom_filter_defs: dict) -> dict | None:
    conditions = []

    if media_type_select.value:
        # Pre-download, media_type is unknown — pass through so the post-download
        # check can evaluate it. Post-download, accept only if type is in the list.
        conditions.append({"any": [
            {"media_type": {"exists": False}},
            {"media_type": {"in": list(media_type_select.value)}},
        ]})

    if dataset_ids:
        conditions.append({"metadata_id": {"in": list(dataset_ids)}})

    if all(v is not None for v in [north.value, south.value, east.value, west.value]):
        conditions.append({"bbox": {
            "north": north.value, "south": south.value,
            "east": east.value,  "west": west.value,
        }})

    if start_date.value and end_date.value:
        if any(inp.error for inp in [start_date, end_date, start_time, end_time]):
            ui.notify(t('validation.date_time_errors'), type='warning')
            return None
        start_t = start_time.value or '00:00'
        end_t = end_time.value or '23:59'
        conditions.append({
            "property": "pubtime",
            "type": "datetime",
            "between": [
                f"{start_date.value}T{start_t}:00+00:00",
                f"{end_date.value}T{end_t}:59+00:00",
            ],
        })

    for fname, inp in custom_inputs.items():
        if inp.value is not None and inp.value != '':
            ftype = custom_filter_defs.get(fname, {}).get('type', 'string')
            if ftype == 'string':
                values = [v.strip() for v in str(inp.value).split(',') if v.strip()]
                conditions.append({"property": fname, "type": ftype, "in": values})
            else:
                conditions.append({"property": fname, "type": ftype, "equals": inp.value})

    if not conditions:
        return {}

    match = {"all": conditions} if len(conditions) > 1 else conditions[0]

    return {
        "rules": [
            {
                "id": "accept",
                "order": 1,
                "match": match,
                "action": "accept",
            },
            {
                "id": "default",
                "order": 999,
                "match": {"always": True},
                "action": "reject",
                "reason": "No filter criteria matched",
            },
        ]
    }


def _collect_per_topic_filters(topics, dataset_select, media_type_select,
                               north, south, east, west,
                               start_date, end_date, start_time, end_time,
                               custom_inputs: dict,
                               custom_filter_defs: dict) -> dict[str, dict] | None:
    """Build a filter per topic, scoping metadata_id to only the datasets that
    belong to that topic and are present in dataset_select.value."""
    selected_ids = set(dataset_select.value or [])
    result = {}
    for topic in topics:
        topic_dataset_ids = [
            d.id for d in get_datasets_for_channel(topic)
            if not selected_ids or d.id in selected_ids
        ]
        f = _build_filter(
            topic_dataset_ids, media_type_select,
            north, south, east, west,
            start_date, end_date, start_time, end_time,
            custom_inputs, custom_filter_defs,
        )
        if f is None:
            return None  # validation error already notified
        result[topic] = f
    return result


def on_topics_picked(e, state, layout, is_page_selection=False, sender=None, dataset_id=None):
    if is_page_selection:
        # Called from catalogue: e.value is [single_topic], toggle in/out
        if e.value[0] not in state.selected_topics:
            state.selected_topics.append(e.value[0])
            if dataset_id and dataset_id not in state.selected_dataset_ids:
                state.selected_dataset_ids.append(dataset_id)
        else:
            state.selected_topics.remove(e.value[0])
            if dataset_id and dataset_id in state.selected_dataset_ids:
                state.selected_dataset_ids.remove(dataset_id)
    else:
        # Called from tree on_select: e.value is the selected node ID or None.
        state.selected_topics = [e.value] if e.value else []
    topics = state.selected_topics

    if not topics:
        layout.right_sidebar.value = False
        layout.right_sidebar.clear()
        return

    layout.right_sidebar.value = True
    with layout.right_sidebar:
        layout.right_sidebar.clear()

        # --- Selected topics ---
        ui.label(t('sidebar.selected_topics')).classes("sidebar-title")
        with ui.row().classes("selected-topics-row"):
            for topic in topics:
                ui.label(topic).classes("selected-topic-chip")

        ui.separator()

        # --- Save directory ---
        directory = ui.input(
            label=t('sidebar.save_directory'),
            placeholder=t('sidebar.save_directory_hint'),
        ).classes("directory-input")

        ui.separator()

        # --- Filters ---
        ui.label(t('sidebar.filters')).classes("sidebar-section-title")

        # Collect datasets for selected topics
        dataset_options: dict[str, str] = {}
        seen_ids: set[str] = set()
        for topic in topics:
            for dataset in get_datasets_for_channel(topic):
                if dataset.id not in seen_ids:
                    seen_ids.add(dataset.id)
                    centre = _centre_id(dataset.id)
                    title = dataset.title or dataset.id
                    label = f"{title} ({centre})" if centre else title
                    dataset_options[dataset.id] = label

        # In the catalogue path, lock the select to the explicitly selected
        # datasets regardless of which card was just toggled. This keeps the
        # select stable when unselecting one of several chosen datasets.
        locked_ids = [did for did in state.selected_dataset_ids if did in dataset_options]
        if is_page_selection and locked_ids:
            dataset_select = ui.select(
                options={did: dataset_options[did] for did in locked_ids},
                label=t('sidebar.dataset') if len(locked_ids) == 1 else t('sidebar.datasets'),
                multiple=True,
                value=locked_ids,
            ).classes("filter-input").props('disable')
        else:
            with ui.row().classes("items-center gap-2"):
                dataset_select = ui.select(
                    options=dataset_options,
                    label=t('sidebar.datasets'),
                    multiple=True,
                ).classes("filter-input")
                ui.button(icon="done_all").props("flat dense round").tooltip(
                    t('btn.select_all')
                ).on(
                    'click',
                    lambda: dataset_select.set_value(
                        list(dataset_options.keys())
                        if not dataset_select.value or len(dataset_select.value) < len(dataset_options)
                        else []
                    ),
                )

        media_type = ui.select(
            options=DEFAULT_ACCEPTED_MEDIA_TYPES,
            label=t('sidebar.media_types'),
            multiple=True,
        ).classes("filter-input")

        # --- Bounding box ---
        with ui.expansion(t('sidebar.bbox'), icon="crop_square").classes("filter-expansion"):
            with ui.grid(columns=2).classes("bbox-grid"):
                north = ui.number(label=t('sidebar.north'), min=-90,  max=90).classes("bbox-input")
                east = ui.number(label=t('sidebar.east'), min=-180, max=180).classes("bbox-input")
                south = ui.number(label=t('sidebar.south'), min=-90, max=90).classes("bbox-input")
                west = ui.number(label=t('sidebar.west'), min=-180, max=180).classes("bbox-input")

        # --- Date & time range ---
        with ui.expansion(t('sidebar.date_range'), icon="date_range").classes("filter-expansion"):
            start_date = ui.input(
                label=t('sidebar.start_date'),
                placeholder=t('sidebar.start_date_hint'),
                validation=lambda v: None if not v or _DATE_RE.match(v) else t('validation.date_format'),
            ).classes("filter-input")
            end_date = ui.input(
                label=t('sidebar.end_date'),
                placeholder=t('sidebar.start_date_hint'),
                validation=lambda v: None if not v or _DATE_RE.match(v) else t('validation.date_format'),
            ).classes("filter-input")
            start_time = ui.input(
                label=t('sidebar.start_time'),
                placeholder=t('sidebar.time_hint'),
                validation=lambda v: None if not v or _TIME_RE.match(v) else t('validation.time_format'),
            ).classes("filter-input")
            end_time = ui.input(
                label=t('sidebar.end_time'),
                placeholder=t('sidebar.time_hint'),
                validation=lambda v: None if not v or _TIME_RE.match(v) else t('validation.time_format'),
            ).classes("filter-input")

        # --- Custom filters from MQTT link metadata (catalogue only) ---
        custom_inputs: dict[str, ui.element] = {}
        custom_filter_defs: dict[str, dict] = {}
        if is_page_selection:
            for topic in topics:
                channel_key = topic.replace("/#", "")
                for dataset in get_datasets_for_channel(topic):
                    for lnk in dataset.links:
                        if lnk.channel and channel_key in lnk.channel:
                            for fname, fdef in lnk.extra.get('filters', {}).items():
                                custom_filter_defs.setdefault(fname, fdef)

            if custom_filter_defs:
                with ui.expansion(t('sidebar.custom_filters'), icon="tune").classes("filter-expansion"):
                    for fname, fdef in custom_filter_defs.items():
                        title = fdef.get('title', fname)
                        description = fdef.get('description', '')
                        ftype = fdef.get('type', 'string')
                        if ftype in ('integer', 'number'):
                            inp = ui.number(label=title).classes("filter-input")
                        else:
                            inp = ui.input(label=title, placeholder='value1, value2, ...').classes("filter-input")
                        if description:
                            inp.tooltip(description)
                        custom_inputs[fname] = inp

        ui.separator()

        def on_subscribe_click():
            confirm_subscribe(
                _collect_per_topic_filters(
                    topics, dataset_select, media_type,
                    north, south, east, west,
                    start_date, end_date, start_time, end_time,
                    custom_inputs, custom_filter_defs,
                ),
                directory.value,
            )

        ui.button(t('btn.subscribe'), icon="check_circle").classes("subscribe-btn").on(
            'click', on_subscribe_click,
        )


def confirm_subscribe(topic_filters: dict | None, directory, credentials=None):
    if topic_filters is None:
        return  # validation errors already shown inline
    if credentials is False:
        return  # credential validation errors already shown inline
    target = directory.strip() or './'

    payloads = [
        {
            "topic": topic,
            "target": target,
            "filter": f,
            **({"credentials": _preview_credentials(credentials)} if credentials else {}),
        }
        for topic, f in topic_filters.items()
    ]
    pretty = json.dumps(payloads if len(payloads) > 1 else payloads[0], indent=2)

    with ui.dialog() as dialog, ui.card().classes("dialog-confirm"):
        ui.label(t('dialog.confirm_title')).classes("sidebar-title")
        with ui.scroll_area():
            ui.code(pretty, language='json').classes("w-full")
        with ui.row().classes("justify-end gap-2"):
            ui.button(t('btn.cancel'), icon="close").props("flat").on('click', dialog.close)

            async def on_confirm():
                dialog.close()
                await subscribe_to_topics(topic_filters, target, credentials)

            ui.button(t('btn.confirm'), icon="check_circle").props("color=primary").on('click', on_confirm)
    dialog.open()


async def subscribe_to_topics(topic_filters: dict, directory, credentials=None):
    async with httpx.AsyncClient() as client:
        for topic, filters in topic_filters.items():
            payload = {
                "topic": topic,
                "target": directory,
                "filter": filters,
            }
            if credentials:
                payload["credentials"] = credentials
            await client.post(f'{SUBSCRIPTION_MANAGER}/subscriptions', json=payload)


async def show_metadata(dataset_id):
    dataset = next(
        (m.record for m in merged_records() if m.record.id == dataset_id),
        None
    )
    with ui.dialog() as dialog, ui.card().classes("dialog-metadata"):
        with ui.scroll_area().classes("dialog-scroll"):
            if dataset is None:
                LOGGER.error(f"Metadata not found for: {dataset_id}")
                ui.label(t('metadata.not_available', id=dataset_id)).classes("result-label")
            else:
                ui.label(t('metadata.id', id=dataset.id)).classes("result-label")
                ui.label(t('metadata.title', title=dataset.title or 'N/A')).classes("result-label")
                ui.label(t('metadata.description', description=dataset.description or 'N/A')).classes("result-description")
                with ui.row():
                    ui.label(t('metadata.keywords')).classes("result-label")
                    for keyword in dataset.keywords:
                        ui.button(keyword).classes("keyword-btn")
                if dataset.geometry:
                    coordinates = copy.deepcopy(dataset.geometry.coordinates)
                    coordinates[0] = coordinates[0][:-1]
                    coordinates = [[(coord[1], coord[0]) for coord in coordinates[0]]]
                    map_widget = ui.leaflet(center=coordinates[0][0], zoom=5, options={'attributionControl': False})
                    map_widget.generic_layer(name='polygon', args=coordinates)
                    map_widget.on('init', lambda ev: map_widget.run_map_method(
                        'fitBounds', [coordinates[0][0], coordinates[0][2]]
                    ))
        ui.button(t('btn.close')).on('click', lambda: dialog.close())
    dialog.open()
