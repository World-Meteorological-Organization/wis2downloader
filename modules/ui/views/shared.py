import copy
import json
import re
import httpx
from nicegui import ui

_DATE_RE = re.compile(r'^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$')
_TIME_RE = re.compile(r'^([01]\d|2[0-3]):[0-5]\d$')

from config import SUBSCRIPTION_MANAGER
from data import get_datasets_for_channel, merged_records

from shared import setup_logging

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


def _centre_id(dataset_id: str) -> str:
    parts = dataset_id.split(':')
    return parts[3] if len(parts) > 3 else ''


def _collect_filters(dataset_select, media_type_select,
                     north, south, east, west,
                     start_date, end_date, start_time, end_time,
                     custom_inputs: dict, custom_filter_defs: dict) -> dict:
    conditions = []

    if media_type_select.value:
        # Pre-download, media_type is unknown — pass through so the post-download
        # check can evaluate it. Post-download, accept only if type is in the list.
        conditions.append({"any": [
            {"media_type": {"exists": False}},
            {"media_type": {"in": list(media_type_select.value)}},
        ]})

    if dataset_select.value:
        conditions.append({"metadata_id": {"in": list(dataset_select.value)}})

    if all(v is not None for v in [north.value, south.value, east.value, west.value]):
        conditions.append({"bbox": {
            "north": north.value, "south": south.value,
            "east": east.value,  "west": west.value,
        }})

    if start_date.value and end_date.value:
        if any(inp.error for inp in [start_date, end_date, start_time, end_time]):
            ui.notify('Fix date/time format errors before subscribing.', type='warning')
            return None
        start_t = start_time.value or '00:00'
        end_t   = end_time.value   or '23:59'
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


def on_topics_picked(e, state, layout, is_page_selection=False, sender=None, dataset_id=None):
    if is_page_selection:
        # Called from catalogue: e.value is [single_topic], toggle in/out
        if e.value[0] not in state.selected_topics:
            state.selected_topics.append(e.value[0])
        else:
            state.selected_topics.remove(e.value[0])
    else:
        # Called from tree on_select: e.value is the selected node ID or None.
        state.selected_topics = [e.value] if e.value else []
    topics = state.selected_topics

    if not topics:
        layout.right_sidebar.value = False
        return

    layout.right_sidebar.value = True
    with layout.right_sidebar:
        layout.right_sidebar.clear()

        # --- Selected topics ---
        ui.label("Selected Topics").classes("sidebar-title")
        with ui.row().classes("selected-topics-row"):
            for topic in topics:
                ui.label(topic).classes("selected-topic-chip")

        ui.separator()

        # --- Save directory ---
        directory = ui.input(
            label='Save directory', placeholder='./'
        ).classes("directory-input")

        ui.separator()

        # --- Filters ---
        ui.label("Filters").classes("sidebar-section-title")

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

        if dataset_id and dataset_id in dataset_options:
            # Catalogue path: single dataset locked to the one selected
            dataset_select = ui.select(
                options={dataset_id: dataset_options[dataset_id]},
                label='Dataset',
                multiple=True,
                value=[dataset_id],
            ).classes("filter-input").props('disable')
        else:
            with ui.row().classes("items-center gap-2"):
                dataset_select = ui.select(
                    options=dataset_options,
                    label='Datasets',
                    multiple=True,
                ).classes("filter-input")
                ui.button(icon="done_all").props("flat dense round").tooltip("Select / deselect all").on(
                    'click',
                    lambda: dataset_select.set_value(
                        list(dataset_options.keys())
                        if not dataset_select.value or len(dataset_select.value) < len(dataset_options)
                        else []
                    ),
                )

        media_type = ui.select(
            options=DEFAULT_ACCEPTED_MEDIA_TYPES,
            label='Media types',
            multiple=True,
        ).classes("filter-input")

        # --- Bounding box ---
        with ui.expansion("Bounding box", icon="crop_square").classes("filter-expansion"):
            with ui.grid(columns=2).classes("bbox-grid"):
                north = ui.number(label='North', min=-90,  max=90).classes("bbox-input")
                east  = ui.number(label='East',  min=-180, max=180).classes("bbox-input")
                south = ui.number(label='South', min=-90,  max=90).classes("bbox-input")
                west  = ui.number(label='West',  min=-180, max=180).classes("bbox-input")

        # --- Date & time range ---
        with ui.expansion("Date & time range", icon="date_range").classes("filter-expansion"):
            start_date = ui.input(
                label='Start date', placeholder='YYYY-MM-DD',
                validation=lambda v: None if not v or _DATE_RE.match(v) else 'Use YYYY-MM-DD',
            ).classes("filter-input")
            end_date = ui.input(
                label='End date', placeholder='YYYY-MM-DD',
                validation=lambda v: None if not v or _DATE_RE.match(v) else 'Use YYYY-MM-DD',
            ).classes("filter-input")
            start_time = ui.input(
                label='Start time (UTC)', placeholder='HH:MM',
                validation=lambda v: None if not v or _TIME_RE.match(v) else 'Use HH:MM (24-hour)',
            ).classes("filter-input")
            end_time = ui.input(
                label='End time (UTC)', placeholder='HH:MM',
                validation=lambda v: None if not v or _TIME_RE.match(v) else 'Use HH:MM (24-hour)',
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
                with ui.expansion("Custom filters", icon="tune").classes("filter-expansion"):
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

        ui.button("Subscribe", icon="check_circle").classes("subscribe-btn").on(
            'click',
            lambda: confirm_subscribe(
                topics,
                directory.value,
                _collect_filters(
                    dataset_select, media_type,
                    north, south, east, west,
                    start_date, end_date, start_time, end_time,
                    custom_inputs, custom_filter_defs,
                ),
            ),
        )


def confirm_subscribe(topics, directory, filters):
    if filters is None:
        return  # validation errors already shown inline
    target = directory.strip() or './'
    payloads = [
        {"topic": topic, "target": target, "filter": filters}
        for topic in topics
    ]
    pretty = json.dumps(payloads if len(payloads) > 1 else payloads[0], indent=2)

    with ui.dialog() as dialog, ui.card().classes("dialog-confirm"):
        ui.label("Confirm Subscription").classes("sidebar-title")
        with ui.scroll_area():
            ui.code(pretty, language='json').classes("w-full")
        with ui.row().classes("justify-end gap-2"):
            ui.button("Cancel", icon="close").props("flat").on('click', dialog.close)

            async def on_confirm():
                dialog.close()
                await subscribe_to_topics(topics, target, filters)

            ui.button("Confirm", icon="check_circle").props("color=primary").on('click', on_confirm)
    dialog.open()


async def subscribe_to_topics(topics, directory, filters):
    async with httpx.AsyncClient() as client:
        for topic in topics:
            payload = {
                "topic": topic,
                "target": directory,
                "filter": filters,
            }
            await client.post(f'{SUBSCRIPTION_MANAGER}/subscriptions', json=payload)


async def show_metadata(dataset_id):
    dataset = next(
        (m.record for m in merged_records() if m.record.id == dataset_id),
        None
    )
    with ui.dialog() as dialog, ui.card():
        with ui.scroll_area().classes("dialog-scroll"):
            if dataset is None:
                LOGGER.error(f"Metadata not found for: {dataset_id}")
                ui.label(f"Metadata not available for: {dataset_id}").classes("result-label")
            else:
                ui.label(f"ID: {dataset.id}").classes("result-label")
                ui.label(f"Title: {dataset.title or 'N/A'}").classes("result-label")
                ui.label(f"Description: {dataset.description or 'N/A'}").classes("result-description")
                with ui.row():
                    ui.label("Keywords:").classes("result-label")
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
        ui.button("Close").on('click', lambda: dialog.close())
    dialog.open()
