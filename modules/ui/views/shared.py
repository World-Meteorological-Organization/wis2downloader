import copy
import httpx
from nicegui import ui

from config import SUBSCRIPTION_MANAGER

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
    layout.right_sidebar.set_value(False)
    layout.right_sidebar.clear()
    layout.dataset_sidebar.clear()
    state.features = {}
    state.selected_topics = []
    state.selected_datasets = {}


def on_topics_picked(e, state, layout, is_page_selection=False, sender=None):
    if len(e.value) == 1:
        if e.value[0] not in state.selected_topics:
            state.selected_topics.append(e.value[0])
        else:
            state.selected_topics.remove(e.value[0])
    else:
        state.selected_topics = e.value
    topics = state.selected_topics

    layout.right_sidebar.set_value(True)
    with layout.right_sidebar:
        layout.right_sidebar.clear()
        ui.label("Selected Topics:").classes("sidebar-title")
        with ui.row().classes("selected-topics-row"):
            for topic in topics:
                ui.label(topic).classes("selected-topic-chip")
        directory = ui.textarea("Directory to save datasets(default: .):").classes("directory-input")
        filters = {}
        ui.button("Select Filters").classes("sidebar-btn").on(
            'click', lambda: show_filters_dialog(topics, filters, state)
        )
        ui.button("Submit").classes("sidebar-btn").on(
            'click', lambda: subscribe_to_topics(topics, directory.value, filters, state)
        )

    with layout.dataset_sidebar:
        layout.dataset_sidebar.clear()
        ui.label("Datasets:").classes("sidebar-title")
        ui.button('Select All', on_click=lambda ev: select_all_datasets(ev, layout))
        added_datasets = []
        with ui.scroll_area().classes("dataset-scroll"):
            for topic in topics:
                for (key, features) in state.features.items():
                    if topic.replace("/#", "") in key:
                        for dataset in features:
                            if dataset['id'] in added_datasets:
                                continue
                            added_datasets.append(dataset['id'])
                            with ui.card().classes("dataset-card"):
                                ui.label(f"{dataset['id']}").classes("break-all dataset-id-label")
                                select_btn = ui.button("Select") \
                                    .classes("dataset-btn") \
                                    .on('click', lambda ev, t=topic, d=dataset['id']:
                                        select_dataset(ev, t, d, state))
                                if is_page_selection and topic == e.value[0]:
                                    select_btn.run_method("click")
                                if dataset['id'] in state.selected_datasets.get(topic, []):
                                    select_btn.text = "Unselect"
                                    select_btn.set_background_color("#77AEE4")
                                ui.button("Show Metadata") \
                                    .classes("dataset-btn") \
                                    .on('click', lambda ev, d=dataset['id']:
                                        show_metadata(d, state))


async def show_filters_dialog(topics, filters, state):
    with ui.dialog() as dialog, ui.card():
        with ui.scroll_area().classes("dialog-scroll"):
            with ui.row():
                north = ui.number(label='North', max=90, min=-90).classes("bbox-input")
                west = ui.number(label='West', max=180, min=-180).classes("bbox-input")
                east = ui.number(label='East', max=180, min=-180).classes("bbox-input")
                south = ui.number(label='South', max=90, min=-90).classes("bbox-input")
            start_date = ui.date_input(label='Start date (YYYY-MM-DD)').classes("dialog-input")
            end_date = ui.date_input(label='End date (YYYY-MM-DD)').classes("dialog-input")
            start_time = ui.time_input(label='Start time (HH:MM)').classes("dialog-input")
            end_time = ui.time_input(label='End time (HH:MM)').classes("dialog-input")
            media_type = ui.select(
                options=DEFAULT_ACCEPTED_MEDIA_TYPES, label='Media Type', multiple=True
            ).classes("dialog-input")
            with ui.column() as custom_filters_column:
                custom_filters = {}
                if len(topics) == 1 and len(state.selected_datasets.get(topics[0], [])) == 1:
                    dataset_id = state.selected_datasets[topics[0]][0]
                    dataset = next(
                        (d for feats in state.features.values() for d in feats if d['id'] == dataset_id),
                        None
                    )
                    if dataset and 'links' in dataset:
                        for link in dataset['links']:
                            if 'filters' in link:
                                for name, filt in link['filters'].items():
                                    if name in custom_filters:
                                        continue
                                    custom_filters[name] = []
                                    ui.button(f"{name}", icon="add").on(
                                        'click',
                                        lambda ev, n=name, t=filt['type']:
                                            add_custom_filter(ev, n, custom_filters_column, t)
                                    )
        with ui.row():
            ui.button("Close").on('click', lambda: dialog.close())
            ui.button("Apply").on('click', lambda: apply_filters(
                filters, north.value, west.value, east.value, south.value,
                start_date.value, end_date.value, start_time.value, end_time.value,
                media_type.value, custom_filters, custom_filters_column
            ))
    dialog.open()


async def apply_filters(filters, north, west, east, south, start_date, end_date,
                        start_time, end_time, media_type, custom_filters, custom_filters_column):
    filters.clear()
    if all([north, west, east, south]):
        filters['bbox'] = [north, west, east, south]
    if start_date and end_date:
        filters['date_range'] = [start_date, end_date]
    if start_time and end_time:
        filters['time_range'] = [start_time, end_time]
    if media_type:
        filters['media_type'] = media_type
    for child in custom_filters_column.descendants():
        if isinstance(child, ui.input):
            custom_filters.setdefault(child.label, []).append(child.value)
    filters['custom_filters'] = custom_filters
    ui.notify(
        "Filters applied. Please click on Submit to save the subscription with the applied filters.",
        type="positive"
    )


async def add_custom_filter(e, name, column, type):
    with column:
        if type == 'string':
            ui.input(label=name).classes("dialog-input")
        elif type == 'datetime':
            ui.date_input(label=name).classes("dialog-input")
        elif type == 'number':
            ui.number(label=name).classes("dialog-input")


async def select_all_datasets(e, layout):
    if e.sender.text == "Select All":
        for child in layout.dataset_sidebar.descendants():
            if isinstance(child, ui.button) and child.text == "Select":
                child.run_method("click")
    else:
        for child in layout.dataset_sidebar.descendants():
            if isinstance(child, ui.button) and child.text == "Unselect":
                child.run_method("click")
    e.sender.text = "Unselect All" if e.sender.text == "Select All" else "Select All"
    e.sender.set_background_color("#77AEE4" if e.sender.text == "Unselect All" else "primary")


async def select_dataset(e, topic, dataset_id, state):
    e.sender.text = "Unselect" if e.sender.text == "Select" else "Select"
    e.sender.set_background_color("#77AEE4" if e.sender.text == "Unselect" else "primary")
    state.selected_datasets.setdefault(topic, [])
    if dataset_id not in state.selected_datasets[topic]:
        state.selected_datasets[topic].append(dataset_id)
    else:
        state.selected_datasets[topic].remove(dataset_id)
        if not state.selected_datasets[topic]:
            del state.selected_datasets[topic]


async def subscribe_to_topics(topics, directory, filters, state):
    async with httpx.AsyncClient() as client:
        if not directory.strip():
            directory = './'
        for topic in topics:
            if topic not in state.selected_datasets:
                continue
            payload = {
                "topic": topic,
                "target": directory,
                "datasets": state.selected_datasets.get(topic, []),
                "filters": filters,
            }
            await client.post(f'{SUBSCRIPTION_MANAGER}/subscriptions', json=payload)


async def show_metadata(dataset_id, state):
    dataset = next(
        (d for feats in state.features.values() for d in feats if d['id'] == dataset_id),
        dataset_id
    )
    with ui.dialog() as dialog, ui.card():
        with ui.scroll_area().classes("dialog-scroll"):
            if isinstance(dataset, str):
                ui.label(f"Metadata not available for: {dataset_id}").classes("result-label")
            else:
                ui.label(f"ID: {dataset['id']}").classes("result-label")
                ui.label(f"Title: {dataset['properties'].get('title', 'N/A')}").classes("result-label")
                ui.label(f"Description: {dataset['properties'].get('description', 'N/A')}").classes("result-description")
                with ui.row():
                    ui.label("Keywords:").classes("result-label")
                    for keyword in dataset['properties'].get('keywords', []):
                        ui.button(keyword).classes("keyword-btn")
                if dataset.get('geometry'):
                    coordinates = copy.deepcopy(dataset['geometry']['coordinates'])
                    coordinates[0] = coordinates[0][:-1]
                    coordinates = [[(coord[1], coord[0]) for coord in coordinates[0]]]
                    map_widget = ui.leaflet(center=coordinates[0][0], zoom=5, options={'attributionControl': False})
                    map_widget.generic_layer(name='polygon', args=coordinates)
                    map_widget.on('init', lambda ev: map_widget.run_map_method(
                        'fitBounds', [coordinates[0][0], coordinates[0][2]]
                    ))
        ui.button("Close").on('click', lambda: dialog.close())
    dialog.open()
