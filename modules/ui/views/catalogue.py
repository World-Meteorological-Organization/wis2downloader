import copy

from nicegui import ui
from shapely.geometry import Point, Polygon, MultiPolygon, MultiPoint

from data import gdc_records, MergedRecord, merged_records
from models.wcmp2 import WCMP2Record

_GDC_CHIP_COLOURS = {'CMA': 'blue', 'DWD': 'teal', 'ECCC': 'orange'}
from views.shared import on_topics_picked, show_metadata, clean_page


class _Event:
    """Minimal event stub so on_topics_picked can be called from search results."""
    def __init__(self, value):
        self.value = value


# ---------------------------------------------------------------------------
# Pure filter helpers (no state dependency)
# ---------------------------------------------------------------------------

def filter_feature(record: WCMP2Record, query: str) -> bool:
    q = query.lower()
    if q in record.id.lower():
        return True
    p = record.properties
    for text in (p.title, p.description, p.version, p.rights):
        if text and q in text.lower():
            return True
    for kw in record.keywords:
        if q in kw.lower():
            return True
    if p.themes:
        for theme in p.themes:
            for concept in theme.concepts:
                for text in (concept.id, concept.title, concept.description):
                    if text and q in text.lower():
                        return True
    return False


def filter_by_data_policy(record: WCMP2Record, data_policy: str) -> bool:
    if data_policy == 'all':
        return True
    return record.wmo_data_policy == data_policy


def filter_by_keywords(record: WCMP2Record, keywords: str) -> bool:
    if not keywords:
        return True
    keyword_list = [kw.strip().lower() for kw in keywords.split(',')]
    record_keywords = [kw.lower() for kw in record.keywords]
    return all(kw in record_keywords for kw in keyword_list)


def filter_by_bbox(record: WCMP2Record, bbox) -> bool | None:
    if not all(v is not None for v in bbox):
        return True
    if record.geometry is not None:
        coordinates = record.geometry.coordinates
        geom_type = record.geometry.type
        bbox_polygon = Polygon(
            [(bbox[1], bbox[3]), (bbox[2], bbox[3]), (bbox[2], bbox[0]), (bbox[1], bbox[0])]
        )
        if geom_type == 'Point':
            return Point(coordinates[0], coordinates[1]).within(bbox_polygon)
        elif geom_type == 'MultiPoint':
            return MultiPoint([(c[0], c[1]) for c in coordinates]).within(bbox_polygon)
        elif geom_type == 'Polygon':
            return Polygon(coordinates[0]).intersects(bbox_polygon)
        elif geom_type == 'MultiPolygon':
            return MultiPolygon([Polygon(part) for part in coordinates[0]]).intersects(bbox_polygon)
    return None  # Preserve original behaviour: None filters record out when bbox is active


# ---------------------------------------------------------------------------
# Search result functions
# ---------------------------------------------------------------------------

async def select_in_search_results(e, page_selector, query, records,
                                   state, layout, sender=None, dataset_id=None):
    on_topics_picked(e, state, layout, is_page_selection=True, sender=sender,
                     dataset_id=dataset_id)
    sender.text = "Unselect" if sender.text == "Select" else "Select"


async def update_search_results(page_selector, query, records: list[MergedRecord], state, layout):
    page_number = int(page_selector.value)
    num_pages = len(page_selector.options)
    parent = page_selector.parent_slot.parent
    parent.clear()
    with parent:
        async def on_page_change_inner(e):
            await update_search_results(page_selector, query, records, state, layout)

        page_selector = ui.select(
            options=[str(i + 1) for i in range(num_pages)],
            label='Page', value=str(page_number), with_input=True,
        ).classes("page-selector").on(
            'update:model-value', on_page_change_inner,
        )
        offset = (page_number - 1) * 10
        event_list = []
        i = 0
        for j in range(offset, offset + 10):
            if j >= len(records):
                break
            merged = records[j]
            rec = merged.record
            with ui.card().classes("result-card"):
                with ui.row().classes("result-card-header"):
                    ui.label(rec.title or rec.id).classes("result-title")
                    if rec.wmo_data_policy:
                        chip_color = "green" if rec.wmo_data_policy == "core" else "red"
                        ui.chip(rec.wmo_data_policy, color=chip_color)
                    for gdc in merged.source_gdcs:
                        ui.chip(gdc, color=_GDC_CHIP_COLOURS.get(gdc, 'grey'))
                    if merged.has_discrepancy:
                        ui.icon('warning', color='orange').tooltip(
                            'Record content differs between catalogues'
                        )

                ui.label(rec.id).classes("result-subtitle")
                with ui.row(wrap=False).classes("result-row"):
                    with ui.column().classes("result-details"):
                        ui.label(rec.description or 'N/A').classes("result-description")
                        with ui.row().classes("result-actions"):
                            ui.button("Show Metadata", icon='info').on(
                                'click',
                                lambda ev, did=rec.id: show_metadata(did),
                            )
                            for lnk in rec.links:
                                if lnk.channel and lnk.channel.startswith('cache/'):
                                    event_list.append(_Event([lnk.channel]))
                                    i += 1
                                    ev_ref = event_list[i - 1]
                                    selector = ui.button("Select", icon='add').on(
                                        'click',
                                        lambda ev, er=ev_ref, did=rec.id: select_in_search_results(
                                            er, page_selector, query, records,
                                            state, layout, sender=ev.sender, dataset_id=did,
                                        ),
                                    )
                                    if lnk.channel in state.selected_topics:
                                        selector.text = "Unselect"
                                    break
                    if rec.geometry is not None:
                        coordinates = copy.deepcopy(rec.geometry.coordinates)
                        coordinates[0] = coordinates[0][:-1]
                        coordinates = [[(c[1], c[0]) for c in coordinates[0]]]
                        map_widget = ui.leaflet(zoom=0, options={'attributionControl': False}).classes("card-map")
                        map_widget.generic_layer(name='polygon', args=coordinates)
                        await map_widget.initialized()
                        map_widget.run_map_method(
                            'fitBounds', copy.deepcopy([coordinates[0][0], coordinates[0][2]])
                        )


async def perform_search(query, data_policy, keywords, bbox, state, layout,
                         results_container):
    clean_page(state, layout)
    results_container.clear()

    records = merged_records()
    records = [m for m in records if filter_feature(m.record, query)]
    records = [m for m in records if filter_by_data_policy(m.record, data_policy)]
    records = [m for m in records if filter_by_keywords(m.record, keywords)]
    records = [m for m in records if filter_by_bbox(m.record, bbox)]

    if not records:
        with results_container:
            ui.label("No results found.").classes("no-results-label")
        return

    num_pages = (len(records) // 10) + (1 if len(records) % 10 > 0 else 0)

    with results_container:
        async def on_page_change(e):
            await update_search_results(page_selector, query, records, state, layout)

        page_selector = ui.select(
            options=[str(i + 1) for i in range(num_pages)],
            label='Page', value='1', with_input=True,
        ).classes("page-selector").on(
            'update:model-value', on_page_change,
        )
        await update_search_results(page_selector, query, records, state, layout)


# ---------------------------------------------------------------------------
# View entry point
# ---------------------------------------------------------------------------

def render(container, state, layout):
    clean_page(state, layout)
    with container:
        ui.label("Catalogue View").classes("page-title")

        if not any(gdc_records.values()):
            with ui.card().classes("info-card"):
                ui.icon('info').classes("info-card-icon")
                ui.label("Catalogue data not loaded").classes("text-h6")
                ui.label(
                    "GDC data is still being fetched. Try again in a moment, "
                    "or visit Settings to trigger a manual refresh."
                ).classes("text-body2 text-grey-7")
            return

        with ui.card().classes("search-form-card"):
            with ui.card_section():
                search_input = ui.input(
                    label='Search topics', placeholder='e.g. surface observations'
                ).classes("search-input")
                with ui.row().classes("filter-row"):
                    search_data_type = ui.select(
                        options=['all', 'core', 'recommended'],
                        label='Data Policy', value='all',
                    ).classes("filter-select")
                    search_keyword = ui.input(
                        label='Keywords (comma-separated)'
                    ).classes("filter-input")
                with ui.row().classes("filter-row"):
                    ui.label("Bounding box:").classes("bbox-label")
                    search_bbox_north = ui.number(label='North', max=90,  min=-90).classes("bbox-input")
                    search_bbox_west  = ui.number(label='West',  max=180, min=-180).classes("bbox-input")
                    search_bbox_east  = ui.number(label='East',  max=180, min=-180).classes("bbox-input")
                    search_bbox_south = ui.number(label='South', max=90,  min=-90).classes("bbox-input")
                with ui.row().classes("justify-end"):
                    search_btn = ui.button('Filter', icon='search')

        results_col = ui.column().classes("results-column")

        search_btn.on(
            'click',
            lambda: perform_search(
                search_input.value,
                search_data_type.value, search_keyword.value,
                [search_bbox_north.value, search_bbox_west.value,
                 search_bbox_east.value, search_bbox_south.value],
                state, layout, results_col,
            ),
        )
