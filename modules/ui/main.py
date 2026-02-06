from cProfile import label
import os
from xmlrpc import client
import httpx
from nicegui import Client, app, ui, binding, context
import json
import copy
from shared import setup_logging
from shapely.geometry import Point, Polygon, MultiPolygon, MultiPoint
from pathlib import Path

ui.add_css('''
    /* Drawer content improvements */
        .q-drawer, .q-drawer--left, .q-drawer--right, .bg-base-100 {
            background-color: #f5f6fa !important;
            margin: 0 !important;
            border-radius: 0 !important;
            box-shadow: none !important;
        }
    .q-drawer .q-label, .q-drawer label, .bg-base-100 .q-label, .bg-base-100 label {
        color: #1a2233 !important;
        font-weight: 700 !important;
        letter-spacing: 0.01em;
        background: transparent !important;
        text-shadow: 0 1px 0 #fff, 0 0px 2px #fff;
    }
    .q-drawer .q-btn, .bg-base-100 .q-btn {
        background: #e6ecf3 !important; /* softer, more natural light blue-gray */
        color: #23405a !important; /* deeper, natural blue for text */
        font-weight: 600 !important;
        border-radius: 8px !important;
        margin-bottom: 6px !important;
        box-shadow: 0 1px 4px 0 rgba(31,38,135,0.06);
        transition: background 0.2s, color 0.2s;
    }
    .q-drawer .q-btn:hover, .q-btn:hover {
        background: #b7c9d9 !important; /* slightly darker on hover */
        color: #2563eb !important;
    }
    .selected-topic-chip {
        background: linear-gradient(90deg, #2563eb 60%, #77AEE4 100%) !important;
        color: #fff !important;
        font-weight: 600 !important;
        border-radius: 7px !important;
        padding: 2px 10px !important;
        font-size: 0.85rem !important;
        margin: 2px 4px 2px 0 !important;
        box-shadow: 0 1px 4px 0 rgba(31,38,135,0.10) !important;
        border: none !important;
        display: inline-flex !important;
        align-items: center !important;
    }
    .q-drawer-container:nth-child(1) > .q-drawer--left {
        margin-left: 0px !important;
    }
    .q-drawer-container:nth-child(2) > .q-drawer--left {
        margin-left: 80px !important;
    }
    .header-bg {
        width: 100vw !important;
        min-height: 120px;
        padding: 0 !important;
        margin: 0 !important;
        overflow: hidden !important;
    }
            background: none !important;
            border-radius: 0 !important;
            box-shadow: none !important;
        }
    .header-img {
        width: 100vw !important;
        height: 120px !important;
        object-fit: cover !important;
        display: block;
        margin: 0 !important;
        padding: 0 !important;
    }

    /* Modern glassmorphism card style */
    .nicegui-card, .q-card {
        background: rgba(255, 255, 255, 0.7) !important;
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.18) !important;
        backdrop-filter: blur(8px) !important;
        border-radius: 18px !important;
        border: 1px solid rgba(255,255,255,0.18) !important;
        margin-bottom: 18px !important;
        transition: box-shadow 0.3s;
    }
    .nicegui-card:hover, .q-card:hover {
        box-shadow: 0 12px 40px 0 rgba(31, 38, 135, 0.22) !important;
    }

    /* Modern button style */
    .q-btn {
        border-radius: 12px !important;
        font-weight: 600 !important;
        box-shadow: 0 2px 8px 0 rgba(31, 38, 135, 0.10) !important;
        transition: background 0.2s, box-shadow 0.2s;
    }
    .q-btn:hover {
        background: #2563eb !important;
        color: #fff !important;
        box-shadow: 0 4px 16px 0 rgba(31, 38, 135, 0.18) !important;
    }

    /* Modern input style */
    .q-field__control, .q-input, .q-select, .q-number {
        border-radius: 10px !important;
        background: rgba(255,255,255,0.85) !important;
        border: 1px solid #e0e7ef !important;
        box-shadow: 0 1px 4px 0 rgba(31, 38, 135, 0.06) !important;
        transition: border 0.2s, box-shadow 0.2s;
    }
    .q-field__control:focus-within, .q-input:focus-within, .q-select:focus-within, .q-number:focus-within {
        border: 1.5px solid #2563eb !important;
        box-shadow: 0 2px 8px 0 rgba(31, 38, 135, 0.12) !important;
    }

    /* Modern label style */
    label, .q-label {
        font-size: 1.08rem !important;
        font-weight: 500 !important;
        color: #1e293b !important;
        letter-spacing: 0.01em;
    }

    /* Sidebar modern look */
    .q-drawer, .q-drawer--left, .q-drawer--right {
        background: rgba(245, 247, 255, 0.92) !important;
        border-radius: 18px !important;
        box-shadow: 0 4px 24px 0 rgba(31, 38, 135, 0.10) !important;
       /* margin: 12px !important;*/
    }

    /* Footer modern look */
    .q-footer {
        background: rgba(32, 106, 170, 0.95) !important;
        border-top-left-radius: 18px !important;
        border-top-right-radius: 18px !important;
        box-shadow: 0 -2px 12px 0 rgba(31, 38, 135, 0.10) !important;
    }

    /* Modern scroll area */
    .q-scrollarea {
        border-radius: 14px !important;
        background: rgba(255,255,255,0.85) !important;
        box-shadow: 0 1px 6px 0 rgba(31, 38, 135, 0.08) !important;
    }

    /* Modern row spacing */
    .q-row {
        gap: 18px !important;
        align-items: center !important;
    }

    /* Modern checkbox: fully round with custom checkmark */
    .q-checkbox__inner {
        background: #fff !important;
        position: relative !important;
        width: 20px !important;
        height: 20px !important;
        min-width: 20px !important;
        min-height: 20px !important;
        transition: background 0.2s, border 0.2s;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        overflow: visible !important;
    }
    .q-checkbox__inner--checked {
        background: #2563eb !important;
        border-color: #2563eb !important;
        .q-footer {
            background: rgba(32, 106, 170, 0.95) !important;
            border-top-left-radius: 0 !important;
            border-top-right-radius: 0 !important;
            box-shadow: none !important;
            margin: 0 !important;
        content: '';
        position: absolute;
        left: 50%;
        .q-drawer, .q-drawer--left, .q-drawer--right {
            background: rgba(245, 247, 255, 0.92) !important;
            border-radius: 0 !important;
            box-shadow: none !important;
            margin: 0 !important;
        border-radius: 1px;
        box-sizing: border-box;
        pointer-events: none;
        display: block;
        z-index: 2;
    }
    /* Modern dialog */
    .q-dialog {
        border-radius: 18px !important;
        background: rgba(255,255,255,0.95) !important;
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.18) !important;
    }
        /* Menu bar gradient background */
    .menu-bar-gradient {
        background: linear-gradient(135deg, #2563eb 60%, #77AEE4 100%) !important;
        box-shadow: 0 4px 24px 0 rgba(31, 38, 135, 0.10) !important;
    }
    .menu-bar-btn.q-btn {
        font-size: 0.68rem !important;
        text-transform: lowercase !important;
        background: #a3c0e6 !important; /* lighter metallic blue */
        color: #23405a !important;
        font-weight: 700 !important;
        border-radius: 10px !important;
        margin-bottom: 4px !important;
        box-shadow: 0 1px 4px 0 rgba(31,38,135,0.13);
        transition: background 0.2s, color 0.2s;
        letter-spacing: 0.01em;
        width: 50px !important;
        min-width: 50px !important;
        max-width: 50px !important;
        height: 30px !important;
        min-height: 30px !important;
        max-height: 30px !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        white-space: nowrap !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        text-align: center !important;
        padding: 0 !important;
        line-height: 28px !important;
    }
    .menu-bar-btn.q-btn:hover {
        background: #2563eb !important;
        color: #fff !important;
    }
''',shared=True)

# Set up logging
setup_logging()  # Configure root logger
LOGGER = setup_logging(__name__)

json_scrapes = {
    "CMA": {},
    "DWD": {},
    "ECCC": {}
}

def scrape_all():
    with httpx.Client() as client:
        for url in [("https://gdc.wis.cma.cn","CMA"), ("https://wis2.dwd.de/gdc", "DWD"), ("https://wis2-gdc.weather.gc.ca", "ECCC")]:
            # if url[1] == "CMA":
            #     continue
            try:
                response = client.get(str(url[0]) + f'/collections/wis2-discovery-metadata/items?limit=2000&f=json', timeout=5)
            except Exception as e:
                LOGGER.error(f"Error fetching data from {url[0]}: {e}")
                response = None
                json_scrapes[url[1]] = {}
                continue
            json_scrape = response.json()
            json_scrapes[url[1]] = json_scrape


scrape_all_task = ui.run(scrape_all())

SUBSCRIPTION_MANAGER = "http://subscription-manager:5001"
app.colors(base_100="#FFFFFF",
           base_200="#5D8FCF",
           base_300="#77AEE4",
           base_400="#206AAA",
           primary   = "#2563eb",
           secondary = "#64748b",
           accent    = "#10b981",
           grey_1 = "#f8fafc",
           grey_2 = "#f1f5f9"           
           )

@ui.page('/')
def home_page(client: Client):
    
    client.content.classes(remove='q-pa-md')

    @binding.bindable_dataclass
    class Tree:
        value: int
        features = {}
        selected_topics = []

        def __init__(self, value):
            self.value = value

    tree = Tree(value= None)

    class Page:
        home = ui.element()
        left_sidebar = ui.element()
        content = ui.element()
        content_card = None
        right_sidebar = ui.element()

        def __init__(self):
            pass
    page = Page()
    

    ui.query(".nicegui-content").style("padding: 0; overflow: hidden;")

    with ui.element("div").classes("flex h-auto w-full relative").style("min-width: 0; margin-left: 320px; margin-right: 340px;"):
        # Content
        page.content = ui.element("div").classes("bg-base-100 h-max p-4 flex-grow min-w-0")
        with page.content:
            view_label = ui.label('Please select a type of display for the topics:').style('font-weight: bold; font-size: 16px;').style('color:' + "#4A72C3" + ';')
            view = ui.radio({'tree':'Tree view', 'page':'Record search'}).props('inline').on('update:model-value', lambda e: on_view_changed(view))

    with ui.header(elevated=True).classes("header-bg bg-white text-slate-900 p-0 flex").style("margin:0 !important; padding:0 !important; border:0 !important; line-height:0 !important;"):
        ui.image('assets/wmo-banner.png').props("fit=cover").classes("header-img").style("width: 100vw; height: 120px; object-fit: cover; display: block; margin: 0 !important; padding: 0 !important; border: 0 !important;")
        ui.image('assets/wmo-foot.png').style("width: 100vw; height: 11px; display: block; margin: 0 !important; padding: 0 !important; border: 0 !important; line-height:0 !important;")
        ui.image('assets/logo.png').style("position: absolute !important; left: 20% !important; top: 20px !important; width: 80px !important; height: 80px !important; line-height:0 !important;")
        
    
    # Left Sidebar
    page.left_sidebar = ui.left_drawer().classes("bg-base-100 p-4").style("width: 240px; min-width: 200px; max-width: 260px; background-color: #f5f6fa;")
    with page.left_sidebar:
        with ui.scroll_area().style('max-height: 75vh; min-height: 200px; width: 100%; overflow-y: auto;'):
            pass  # Place dataset elements here in your actual code
    
    # MenuBar
    page.home = ui.left_drawer().props("mini mini-width=80").classes("menu-bar-gradient p-4 items-center justify-start gap-4")
    with page.home:
        ui.button(icon='subscribe',text="GDC Subscription").props("mini mini-width=80 no-caps").classes("menu-bar-btn").style("width: 80px !important; min-width: 80px !important; max-width: 80px !important;").on('click', lambda: ui.navigate.to('/'))
        ui.button(icon='unsubscribe',text="Unsubscribe").props("mini mini-width=80 no-caps").classes("menu-bar-btn").style("width: 80px !important; min-width: 80px !important; max-width: 80px !important;").on('click', lambda: ui.navigate.to('/unsubscribe'))



    # Right Sidebar
    page.right_sidebar = ui.right_drawer().classes("w-[20%] max-w-sm bg-base-100 p-4").style("background-color: #f5f6fa;")
    with page.right_sidebar:
        pass

    #Footer
    with ui.footer().classes("bg-base-400").style("height: 30px;"):
        ui.image('assets/wmo-foot.png').style("margin-top: -10px; height: 11px;")
        ui.label("© 2026 World Meteorological Organization").style("color: white; margin-left: 10px; font-size: 12px; margin-top: -18px;")





    def put_in_dicc(dicc,key,identifier):
        values = key.split('/')
        if len(values) == 1:
            if identifier == "cache":
                dicc["id"] = "cache/#"
            elif values[0] not in dicc:
                dicc["id"] = identifier
                dicc["label"] = values[0]
        else:
            dicc["id"] = identifier.split("/" + values[0] + "/")[0]+ "/" + values[0] + "/#"
            dicc["label"] = values[0]
            if dicc["label"] == 'cache':
                dicc['id'] = 'cache/#'
            if "children" not in dicc:
                dicc["children"] = []
            for child in dicc["children"]:
                if child["id"].split('/')[-2] == values[1]:
                    put_in_dicc(child, '/'.join(values[1:]),identifier)
                    return dicc
            new_dicc = {}
            dicc["children"].append(new_dicc)
            put_in_dicc(new_dicc, '/'.join(values[1:]), identifier)
        return dicc

    async def on_view_changed(e):
        if page.content_card is not None:
            page.content_card.delete()
        with ui.card() as content_card:
            page.content_card = content_card
            content_card.set_visibility(True)
            for child in content_card.descendants():
                child.delete()
            tree.value = None
            tree.selected_topics = []
            page.left_sidebar.clear()
            page.right_sidebar.clear()
            label = ui.label("Please select a source GDC.").style('margin-left: 10px; font-weight: bold;').style('color: black;')
            if e.value == 'tree':
                url = radio1 = ui.radio({"CMA":'CMA', "DWD":'DWD', "ECCC":"ECCC" }).props('inline').on('update:model-value', lambda e: scrape_topics_tree(url.value))
            else:
                url = radio1 = ui.radio({"CMA":'CMA', "DWD":'DWD', "ECCC":"ECCC" }).props('inline').on('update:model-value', lambda e: make_search_page(e.sender, url.value))

    async def make_search_page(e, gdc):
        with page.content_card:
            page.content_card.clear()
            label = ui.label("Please select a source GDC.").style('margin-left: 10px; font-weight: bold;').style('color: black;')
            url = radio1 = ui.radio({"CMA":'CMA', "DWD":'DWD', "ECCC":"ECCC" },value=e.value).props('inline').on('update:model-value', lambda e: make_search_page(e.sender, url.value))
            with ui.row() as search_row:
                search_row.tag = "search_row"
                search_input = ui.input(label='Search topics').style('width: 100%;')
            with ui.row() as filters_row:
                filters_row.tag = "filters_row"
                search_data_type = ui.select(options=['all','core','recommended'], label='Data Policy', value='all').style('width: 15vh')
                search_keyword = ui.input(label='Keywords use (,)s').style('width: 15vh;')
            with ui.row() as bbox_row:
                bbox_row.tag = "bbox_row"
                search_bbox_north = ui.number(label='North',max=90, min=-90).style('width: 10vh;')
                search_bbox_west = ui.number(label='West',max=180, min=-180).style('width: 10vh;')
                search_bbox_east = ui.number(label='East',max=180, min=-180).style('width: 10vh;')
                search_bbox_south = ui.number(label='South',max=90, min=-90).style('width: 10vh;')
            with ui.row() as button_row:
                search_button = ui.button('Search').style('margin-left: 10px;').on('click', lambda: perform_search(search_input.value,gdc,search_data_type.value,search_keyword.value,[search_bbox_north.value,search_bbox_west.value,search_bbox_east.value,search_bbox_south.value]))
                button_row.tag = "search_button"

    def filter_feature(feature, query):
        if feature.get("id") is not None and query.lower() in feature['id'].lower():
            return True
        if 'properties' in feature:
            for key, value in feature['properties'].items():
                if isinstance(value, str) and query.lower() in value.lower():
                    return True
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, str) and query.lower() in item.lower():
                            return True
        return False
    
    def filter_by_data_policy(feature, data_policy):
        if data_policy == 'all':
            return True
        if 'properties' in feature and 'wmo:dataPolicy' in feature['properties']:
            return feature['properties']['wmo:dataPolicy'] == data_policy
        return False
    
    def filter_by_keywords(feature, keywords):
        if not keywords:
            return True
        keyword_list = [kw.strip().lower() for kw in keywords.split(',')]
        if 'properties' in feature and 'keywords' in feature['properties']:
            feature_keywords = [kw.lower() for kw in feature['properties']['keywords']]
            for kw in keyword_list:
                if kw not in feature_keywords:
                    return False
            return True
        return False
    
    def filter_by_bbox(feature, bbox):
        if not all(bbox):
            return True
        if 'geometry' in feature and feature['geometry'] is not None:
            coordinates = feature['geometry']['coordinates']
            type = feature['geometry']['type']
            if type == 'Point':
                point = Point(coordinates[0], coordinates[1])
                bbox_polygon = Polygon([(bbox[1], bbox[3]), (bbox[2], bbox[3]), (bbox[2], bbox[0]), (bbox[1], bbox[0])])
                return point.within(bbox_polygon)
            elif type == 'MultiPoint':
                multipoint = MultiPoint([(coord[0], coord[1]) for coord in coordinates])
                bbox_polygon = Polygon([(bbox[1], bbox[3]), (bbox[2], bbox[3]), (bbox[2], bbox[0]), (bbox[1], bbox[0])])
                return multipoint.within(bbox_polygon)
            elif type in ['Polygon', 'MultiPolygon']:
                if type == 'Polygon':
                    polygon = Polygon(coordinates[0])
                else:
                    polygon = MultiPolygon([Polygon(part) for part in coordinates[0]])
                bbox_polygon = Polygon([(bbox[1], bbox[3]), (bbox[2], bbox[3]), (bbox[2], bbox[0]), (bbox[1], bbox[0])])
                return polygon.intersects(bbox_polygon)
            
    
    async def perform_search(query, gdc, data_policy, keywords, bbox):
        page.right_sidebar.clear()
        page.left_sidebar.clear()
        with page.content_card:
            for child in page.content_card.descendants():
                if child.tag in ["results_column", "results_label"]:
                    child.delete()
                    ui.update()
            json = copy.deepcopy(json_scrapes[gdc])
            features = [feature for feature in json['features'] if filter_feature(feature, query)]
            features = [feature for feature in features if filter_by_data_policy(feature, data_policy)]
            features = [feature for feature in features if filter_by_keywords(feature, keywords)]
            features = [feature for feature in features if filter_by_bbox(feature, bbox)]
            if len(features) == 0:
                results_label = ui.label("No results found.").style('margin-top: 10px; font-weight: bold;').style('color: black;')
                results_label.tag = "results_label"
                return
            json['features'] = features
            # for feature in json['features']:
            #     if feature.contains(query):
            #         features.append(feature)
            tree.features = {}
            tree.selected_topics = []
            tree.value = None
            for item in json['features']:
                for link in item['links']:
                    if "channel" in link and link["channel"].startswith('cache/'):
                        if link["channel"] not in tree.features:
                            tree.features[link["channel"]] = []
                        tree.features[link["channel"]].append(item)
                        break
            total_matched = len(json["features"])
            num_pages = (total_matched // 10) + (1 if total_matched % 10 > 0 else 0)
            
            with ui.column() as results_column:
                results_column.tag = "results_column"
                page_selector = ui.select(options=[str(i+1) for i in range(num_pages)], label='Page', value='1', with_input=True).style('width: 10vh;').on('update:model-value', lambda e: update_search_results(page_selector, query, gdc, json))
                await update_search_results(page_selector, query, gdc, json)

    async def update_search_results(page_selector, query, gdc, filtered_json):
        page_number = int(page_selector.value)
        num_pages = len(page_selector.options)
        page_selector.parent_slot.parent.clear()
        with page_selector.parent_slot.parent as results_column:
            page_selector = ui.select(options=[str(i+1) for i in range(num_pages)], label='Page', value=str(page_number), with_input=True).style('width: 10vh;').on('update:model-value', lambda e: update_search_results(page_selector, query, gdc,filtered_json))
            offset = (page_number - 1) * 10
            json = filtered_json
            tree_list = []
            i = 0
            for j in range(offset, offset + 10):
                if j >= len(json['features']):
                    break
                item = json['features'][j]
                with ui.card().tight().style('margin-top: 10px; max-width: 60vh'):
                    ui.label(f"ID: {item['id']}").style('font-weight: bold;')
                    ui.label(f"Title: {item['properties'].get('title', 'N/A')}").style('font-weight: bold;')
                    ui.label(f"Description: {item['properties'].get('description', 'N/A')}").style('font-weight: bold; text-overflow: ellipsis;word-wrap: break-word; overflow: hidden; max-height: 4.2em;')
                    with ui.row():
                        ui.button("Show Metadata").on('click', lambda e, dataset_id=item['id']: show_metadata(dataset_id))       
                        for item_link in item['links']:
                            if "channel" in item_link and item_link["channel"].startswith('cache/'):
                                tree_list.append(Tree([item_link['channel']]))
                                i+=1
                                selector = ui.button("Select").on('click', lambda e, tree=tree_list[i-1]: on_topics_picked(tree,sender=e.sender) and update_search_results(page_selector, query, gdc, filtered_json))
                                if item_link['channel'] in tree.selected_topics:
                                    selector.text = "Deselect"
                                break   

    async def scrape_topics_tree(gdc):
        with page.content_card:
            json = json_scrapes[gdc]
            ui.update()
            tree.features = {}
            dicc = {}
            for item in json['features']:
                for link in item['links']:
                    if "channel" in link and link["channel"].startswith('cache/'):
                        if link["channel"] not in tree.features:
                            tree.features[link["channel"]] = []
                        tree.features[link["channel"]].append(item)
                        dicc = put_in_dicc(dicc, link["channel"], link["channel"])
                        break  
            if tree.value is not None:
                for ancestor in tree.value.ancestors():
                    ancestor.delete()
                    break
            with ui.scroll_area().style('height: 90vh;'):
                filter = ui.input(label='Filter topics')
                new_tree = ui.tree([dicc], label_key='label', tick_strategy='strict', on_tick=lambda e: on_topics_picked(e))
                filter.bind_value_to(new_tree, 'filter')
                tree.value = new_tree
            label.text = ''

    def on_topics_picked(e,sender=None):
        if len(e.value) == 1:
            if e.value[0] not in tree.selected_topics:
                tree.selected_topics.append(e.value[0])
            else:
                tree.selected_topics.remove(e.value[0])
        else:
            tree.selected_topics = e.value
        topics = tree.selected_topics
        with page.right_sidebar:
            page.right_sidebar.clear()
            ui.label("Selected Topics:").style('font-weight: bold; font-size: 16px;').style('color:' + "#4A72C3" + ';')
            with ui.row().classes("selected-topics-row"):
                for topic in topics:
                    ui.label(topic).classes("selected-topic-chip").style("display: inline-flex; align-items: center; padding: 2px 10px; border-radius: 7px; background: linear-gradient(90deg, #77AEE4 60%, #2563eb 100%); color: #fff; font-weight: 500; font-size: 0.85rem; margin: 2px 4px 2px 0; box-shadow: 0 1px 4px 0 rgba(31,38,135,0.10);")
            directory = ui.textarea("Directory to save datasets(default: data):").style('margin-top: 10px; width: 100%;')
            submit = ui.button("Submit").style('margin-top: 10px;').on('click', lambda: subscribe_to_topics(topics, directory.value))
        with page.left_sidebar:
            page.left_sidebar.clear()
            ui.label("Datasets:").style('font-weight: bold; font-size: 16px;').style('color:' + "#4A72C3" + ';')
            with ui.scroll_area().style('height: 90vh;'):
                for topic in topics:
                        for (key,features) in tree.features.items():
                            if topic[0:-2] in key:
                                for dataset in features:
                                    ui.button(f"{dataset['id']}").style('font-size:12px;width:70%').on('click', lambda e: show_metadata(e.sender.text))
    
    async def subscribe_to_topics(topics, directory):
        async with httpx.AsyncClient() as client:
            if directory.strip() == '':
                directory = 'data'
            for topic in topics:
                payload = {
                    "topic": topic,
                    "target": directory
                }
                response = await client.post(f'{SUBSCRIPTION_MANAGER}/subscriptions', json=payload)

    async def show_metadata(dataset):
        for (key,features) in tree.features.items():
            for data in features:
                if data['id'] == dataset:
                    dataset = data
                    break
        with ui.dialog() as dialog, ui.card():
            with ui.scroll_area().style('width: 400px;'):
                ui.label(f"ID: {dataset['id']}").style('font-weight: bold;')
                ui.label(f"Title: {dataset['properties'].get('title', 'N/A')}").style('font-weight: bold;')
                ui.label(f"Description: {dataset['properties'].get('description', 'N/A')}").style('font-weight: bold; text-overflow: ellipsis;word-wrap: break-word; overflow: hidden; max-height: 4.2em;')
                with ui.row():
                    ui.label("Keywords:").style('font-weight: bold;')
                    for keyword in dataset['properties'].get('keywords', []):
                        ui.button(f"{keyword}").style('font-size: 12px;')
                if 'geometry' in dataset and dataset['geometry'] is not None:
                    coordinates = dataset['geometry']['coordinates']
                    coordinates[0]= coordinates[0][:-1]
                    coordinates = [[(coord[1], coord[0]) for coord in coordinates[0]]]
                    map = ui.leaflet()
                    location = map.generic_layer(name='polygon',args=coordinates)
                    map.on('init', lambda e: map.run_map_method('fitBounds', [coordinates[0][0], coordinates[0][2]]))
            ui.button("Close").on('click', lambda: dialog.close())
        dialog.open()


@ui.page('/unsubscribe')
def unsuscribe_page():
    class Page:
        home = ui.element()
        left_sidebar = ui.element()
        content = ui.element()
        right_sidebar = ui.element()
        subscriptions = {}
    page = Page()

    ui.query(".nicegui-content").style("padding: 0; overflow: hidden;")

    with ui.element("div").classes("flex w-full h-screen absolute"):
            # MenuBar
        page.home = ui.element("div").classes("flex flex-col w-xs bg-base-400 p-4 items-center justify-start gap-4")
        with page.home:
                ui.button(icon="home", text="GDC Subscription", color="base-100").props("flat round").on('click', lambda: ui.navigate.to('/'))
                ui.button(icon="logout", text="Unsubscribe", color="base-100").props("flat round").on('click', lambda: ui.navigate.to('/unsuscribe'))

            # Content
        page.content = ui.element("div").classes("grow bg-base-100 p-4")
        with page.content:
            reload = ui.button("Reload Subscriptions").style('margin-left: 10px; font-weight: bold;').on('click', lambda: load_subscriptions())
            # Right Sidebar
        page.right_sidebar = ui.element("div").classes("w-[20%] max-w-xs bg-base-200 p-4")
        with page.right_sidebar:
            pass

    async def load_subscriptions():
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{SUBSCRIPTION_MANAGER}/subscriptions')
            page.subscriptions = response.json()
            for element in page.content.descendants():
                if element is not reload and element is not page.content:
                    element.delete()
            with page.content:
                scroll_area = ui.scroll_area().style('height: 90vh;') 
            with scroll_area:
                for (sub) in page.subscriptions:
                    with ui.row():
                        ui.label(f"Topic: {sub}").style('margin-left: 10px; font-weight: bold;').style('color: black;')
                        ui.label(f"Folder: {page.subscriptions[sub]['save_path']}").style('margin-left: 10px; font-weight: bold;').style('color: black;')
                        ui.button("Unsubscribe").style('margin-left: 10px;').on('click', lambda e: unsubscribe(e.sender.parent_slot.children[0].text.replace('Topic: ', '')))
    
    async def unsubscribe(sub_id):
        async with httpx.AsyncClient() as client:
            sub_id = sub_id.replace('#', '%23')
            sub_id = sub_id.replace('+', '%2B')
            response = await client.delete(f'{SUBSCRIPTION_MANAGER}/subscriptions/{sub_id}')
            await load_subscriptions()


ui.run()
