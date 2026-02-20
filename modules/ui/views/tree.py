from nicegui import ui

from data import gdc_records, merged_records
from views.shared import on_topics_picked, clean_page


# ---------------------------------------------------------------------------
# Pure tree-builder helper
# ---------------------------------------------------------------------------

def put_in_dicc(dicc, key, identifier):
    values = key.split('/')
    if len(values) == 1:
        if identifier == "cache":
            dicc["id"] = "cache/#"
        elif values[0] not in dicc:
            dicc["id"] = identifier
            dicc["label"] = values[0]
    else:
        dicc["id"] = identifier.split("/" + values[0] + "/")[0] + "/" + values[0] + "/#"
        dicc["label"] = values[0]
        if dicc["label"] == 'cache':
            dicc['id'] = 'cache/#'
        if "children" not in dicc:
            dicc["children"] = []
        for child in dicc["children"]:
            if child["id"].split('/')[-2] == values[1]:
                put_in_dicc(child, '/'.join(values[1:]), identifier)
                return dicc
        new_dicc = {}
        dicc["children"].append(new_dicc)
        put_in_dicc(new_dicc, '/'.join(values[1:]), identifier)
    return dicc


# ---------------------------------------------------------------------------
# GDC scraper — builds state.features + tree widget
# ---------------------------------------------------------------------------

async def scrape_topics_tree(state, layout, tree_area):
    clean_page(state, layout)
    dicc = {}
    for merged in merged_records():
        for channel in merged.record.mqtt_channels:
            if channel.startswith('cache/'):
                state.features.setdefault(channel, []).append(merged.record)
                dicc = put_in_dicc(dicc, channel, channel)
                break

    tree_area.clear()
    with tree_area:
        filter_input = ui.input(label='Filter topics')
        tree_widget = ui.tree(
            [dicc], label_key='label', tick_strategy='strict',
            on_tick=lambda e: on_topics_picked(e, state, layout),
        )
        filter_input.bind_value_to(tree_widget, 'filter')
        state.tree_widget = tree_widget


# ---------------------------------------------------------------------------
# View entry point
# ---------------------------------------------------------------------------

def render(container, state, layout):
    clean_page(state, layout)
    with container:
        ui.label("Tree Search").classes("page-title")

        if not any(gdc_records.values()):
            with ui.card().classes("info-card"):
                ui.icon('info').classes("info-card-icon")
                ui.label("Catalogue data not loaded").classes("text-h6")
                ui.label(
                    "GDC data is still being fetched. Try again in a moment, "
                    "or visit Settings to trigger a manual refresh."
                ).classes("text-body2 text-grey-7")
            return

        with ui.scroll_area().classes("tree-scroll") as tree_area:
            ui.label("Loading…").classes("text-body2 text-grey-7")

        ui.timer(0.1, lambda: scrape_topics_tree(state, layout, tree_area), once=True)
