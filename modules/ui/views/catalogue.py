import copy

from nicegui import ui
from shapely.geometry import Point, Polygon, MultiPolygon, MultiPoint

from data import gdc_records, MergedRecord, merged_records
from models.wcmp2 import WCMP2Record
from i18n import t

from shared import setup_logging

from views.shared import on_topics_picked, show_metadata, clean_page

_GDC_CHIP_COLOURS = {'CMA': 'blue', 'DWD': 'teal', 'ECCC': 'orange'}
setup_logging()
LOGGER = setup_logging(__name__)

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


def filter_by_bbox(record: WCMP2Record, bbox, spatial_rel = 'intersects') -> bool :
    if not all(v is not None for v in bbox):
        return True

    if record.geometry is None:
        return False

    coordinates = record.geometry.coordinates
    geom_type = record.geometry.type
    bbox_polygon = Polygon(
        [(bbox[1], bbox[3]), (bbox[2], bbox[3]), (bbox[2], bbox[0]), (bbox[1], bbox[0])]
    )

    # convert to shapely geometry
    if geom_type == 'Point':
        geom = Point(coordinates[0], coordinates[1])
    elif geom_type == 'MultiPoint':
        geom = MultiPoint([(c[0], c[1]) for c in coordinates])
    elif geom_type == 'Polygon':
        geom = Polygon(coordinates[0])
    elif geom_type == 'MultiPolygon':
        geom = MultiPolygon([Polygon(part) for part in coordinates[0]])
    else:
        LOGGER.warning(f"Unsupported geometry type '{geom_type}' in bbox filter; rejecting")
        return False

    # apply filter
    return geom.within(bbox_polygon) if spatial_rel == 'within' else geom.intersects(bbox_polygon)

# ---------------------------------------------------------------------------
# Search result functions
# ---------------------------------------------------------------------------

async def select_in_search_results(e, page_selector, query, records,
                                   state, layout, sender=None, dataset_id=None):
    on_topics_picked(e, state, layout, is_page_selection=True, sender=sender,
                     dataset_id=dataset_id)
    sender.text = t('btn.unselect') if e.value[0] in state.selected_topics else t('btn.select')


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
            label=t('catalogue.page'), value=str(page_number), with_input=True,
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
                        ui.icon('warning', color='orange').props(
                            f'aria-label="{t("aria.discrepancy")}" role="img"'
                        ).tooltip(t('catalogue.discrepancy'))

                ui.label(rec.id).classes("result-subtitle")
                with ui.row(wrap=False).classes("result-row"):
                    with ui.column().classes("result-details"):
                        ui.label(rec.description or 'N/A').classes("result-description")
                        with ui.row().classes("result-actions"):
                            ui.button(t('btn.show_metadata'), icon='info').on(
                                'click',
                                lambda ev, did=rec.id: show_metadata(did),
                            )
                            for lnk in rec.links:
                                if lnk.channel and lnk.channel.startswith('cache/'):
                                    event_list.append(_Event([lnk.channel]))
                                    i += 1
                                    ev_ref = event_list[i - 1]
                                    btn_text = t('btn.unselect') if lnk.channel in state.selected_topics else t('btn.select')
                                    selector = ui.button(btn_text, icon='add').on(
                                        'click',
                                        lambda ev, er=ev_ref, did=rec.id: select_in_search_results(
                                            er, page_selector, query, records,
                                            state, layout, sender=ev.sender, dataset_id=did,
                                        ),
                                    )
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


async def perform_search(query, data_policy, keywords, bbox, spatial_rel,
                         state, layout, results_container):
    clean_page(state, layout)
    results_container.clear()

    records = merged_records()
    records = [m for m in records if filter_feature(m.record, query)]
    records = [m for m in records if filter_by_data_policy(m.record, data_policy)]
    records = [m for m in records if filter_by_keywords(m.record, keywords)]
    records = [m for m in records if filter_by_bbox(m.record, bbox, spatial_rel)]

    if not records:
        with results_container:
            ui.label(t('catalogue.no_results')).classes("no-results-label")
        return

    num_pages = (len(records) // 10) + (1 if len(records) % 10 > 0 else 0)

    with results_container:
        async def on_page_change(e):
            await update_search_results(page_selector, query, records, state, layout)

        page_selector = ui.select(
            options=[str(i + 1) for i in range(num_pages)],
            label=t('catalogue.page'), value='1', with_input=True,
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
        with ui.column().classes("catalogue-page"):
            ui.label(t('catalogue.title')).classes("page-title")
            if not any(gdc_records.values()):
                with ui.card().classes("info-card"):
                    ui.icon('info').classes("info-card-icon")
                    ui.label(t('catalogue.not_loaded')).classes("text-h6")
                    ui.label(t('catalogue.not_loaded_msg')).classes("text-body2 text-grey-7")
                return

            with ui.card().classes("search-form-card"):
                with ui.card_section():
                    # Free text filter
                    search_input = ui.input(
                        label=t('catalogue.search_label'),
                        placeholder=t('catalogue.search_hint'),
                    ).classes("search-input")
                    with ui.row().classes("filter-row"):
                        # Data policy filter
                        search_data_type = ui.select(
                            options=['all', 'core', 'recommended'],
                            label=t('catalogue.data_policy'), value='all',
                        ).classes("filter-select")
                        # keyword filter
                        search_keyword = ui.input(
                            label=t('catalogue.keywords_label')
                        ).classes("filter-input")
                    with ui.row().classes("filter-row"):
                        # Bounding box filter
                        ui.label(t('catalogue.bbox_label')).classes("bbox-label")
                        search_bbox_north = ui.number(label=t('sidebar.north'), max=90,  min=-90).classes("bbox-input")
                        search_bbox_west  = ui.number(label=t('sidebar.west'),  max=180, min=-180).classes("bbox-input")
                        search_bbox_east  = ui.number(label=t('sidebar.east'),  max=180, min=-180).classes("bbox-input")
                        search_bbox_south = ui.number(label=t('sidebar.south'), max=90,  min=-90).classes("bbox-input")
                    with ui.row().classes("filter-row"):
                        ui.label(t('catalogue.bbox_spatial_rel')).classes("bbox-label")
                        search_spatial_rel = ui.radio(
                            {'intersects': t('catalogue.bbox_intersects'), 'within': t('catalogue.bbox_within')},
                            value='intersects',
                        ).props('inline')
                    with ui.row().classes("justify-end"):
                        search_btn = ui.button(t('btn.filter'), icon='search')

            results_col = ui.column().classes("results-column")

            search_btn.on(
                'click',
                lambda: perform_search(
                    search_input.value,
                    search_data_type.value, search_keyword.value,
                    [search_bbox_north.value, search_bbox_west.value,
                     search_bbox_east.value, search_bbox_south.value],
                    search_spatial_rel.value,
                    state, layout, results_col,
                ),
            )
