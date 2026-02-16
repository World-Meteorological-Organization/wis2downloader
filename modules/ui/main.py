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

app.add_static_files('/assets', 'assets')
ui.add_head_html('<link rel="stylesheet" type="text/css" href="/assets/base.css">',shared=True)

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
        selected_datasets = {}

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

    # Use a flex row: main content + sidebar (sidebar is not fixed)
    with ui.element("div").classes("flex flex-row h-full w-full relative").style("margin-top: -7vh;"):
        # Main content area
        with ui.element("div").classes("flex-grow min-w-0 bg-base-100 h-full") as content:
            page.content = content
            view_label = ui.label('Please select a type of display for the topics:').style('font-weight: bold; font-size: 16px;').style('color:' + "#4A72C3" + ';')
            view = ui.radio({'tree':'Tree view', 'page':'Record search'}).props('inline').on('update:model-value', lambda e: on_view_changed(view))
        # Dataset Sidebar as a column on the right
        dataset_sidebar = ui.element("div").classes("bg-base-100 p-4 dataset-sidebar").style("width: 260px; background-color: #f5f6fa; box-shadow: -2px 0 8px rgba(31,38,135,0.06);")
        with dataset_sidebar:
            page.dataset_sidebar = dataset_sidebar

    with ui.header(elevated=True).classes("header-bg bg-white text-slate-900 p-0 flex").style("margin:0 !important; padding:0 !important; border:0 !important; line-height:0 !important;"):
        ui.image('assets/wmo-banner.png').props("fit=cover").classes("header-img").style("width: 100vw; height: 120px; object-fit: cover; display: block; margin: 0 !important; padding: 0 !important; border: 0 !important;")
        ui.image('assets/wmo-foot.png').style("width: 100vw; height: 11px; display: block; margin: 0 !important; padding: 0 !important; border: 0 !important; margin-top: -17px !important;")
        ui.image('assets/logo.png').style("position: absolute !important; left: 20% !important; top: 20px !important; width: 80px !important; height: 80px !important; line-height:0 !important;")
    
    # MenuBar
    page.home = ui.left_drawer().props("mini mini-width=80").classes("menu-bar-gradient p-4 items-center justify-start gap-4")
    with page.home:
        ui.button(icon='subscribe', text="GDC Subscription").props("no-caps").classes("menu-bar-btn").on('click', lambda: ui.navigate.to('/'))
        ui.button(icon='unsubscribe', text="Remove Subscription").props("no-caps").classes("menu-bar-btn").on('click', lambda: ui.navigate.to('/unsubscribe'))



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
            page.dataset_sidebar.clear()
            page.right_sidebar.clear()
            label = ui.label("Please select a source GDC.").style('margin-left: 10px; font-weight: bold;').style('color: black;')
            if e.value == 'tree':
                url = radio1 = ui.radio({"CMA":'CMA', "DWD":'DWD', "ECCC":"ECCC" }).props('inline').on('update:model-value', lambda e: scrape_topics_tree(url.value))
            else:
                url = radio1 = ui.radio({"CMA":'CMA', "DWD":'DWD', "ECCC":"ECCC" }).props('inline').on('update:model-value', lambda e: make_search_page(e.sender, url.value))

    async def make_search_page(e, gdc):
        clean_page()
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
        clean_page()
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
            for item in json['features']:
                for link in item['links']:
                    if "channel" in link and link["channel"].startswith('cache/'):
                        if link["channel"] not in tree.features:
                            tree.features[link["channel"]] = []
                        tree.features[link["channel"]].append(item)
                        break
            total_matched = len(json["features"])
            num_pages = (total_matched // 10) + (1 if total_matched % 10 > 0 else 0)
            
            with ui.column().style("width: 100%;") as results_column:
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
                with ui.card().tight().style('width: 70%; max-width: 100%;'):
                    with ui.row(wrap=False).style('width: 70%;'):
                        with ui.column().style('max-width: 55vh;'):
                            ui.label(f"ID: {item['id']}").style('font-weight: bold;')
                            ui.label(f"Title: {item['properties'].get('title', 'N/A')}").style('font-weight: bold;')
                            ui.label(f"Description: {item['properties'].get('description', 'N/A')}").style('font-weight: bold; text-overflow: ellipsis;word-wrap: break-word; overflow: hidden; max-height: 4.2em;')
                            with ui.row():
                                ui.button("Show Metadata").on('click', lambda e, dataset_id=item['id']: show_metadata(dataset_id))       
                                for item_link in item['links']:
                                    if "channel" in item_link and item_link["channel"].startswith('cache/'):
                                        tree_list.append(Tree([item_link['channel']]))
                                        i+=1
                                        selector = ui.button("Select").on('click', lambda e, tree=tree_list[i-1]: select_in_search_results(tree, page_selector=page_selector, query=query, gdc=gdc, filtered_json=filtered_json, sender=e.sender))
                                        if item_link['channel'] in tree.selected_topics:
                                            selector.text = "Unselect"
                                        break
                        if 'geometry' in item and item['geometry'] is not None:
                            coordinates = copy.deepcopy(item['geometry']['coordinates'])
                            coordinates[0]= coordinates[0][:-1]
                            coordinates = [[(coord[1], coord[0]) for coord in coordinates[0]]]
                            map = ui.leaflet(zoom=0).classes("card-map").style('width: 60%; max-width: 60%; height: 200px; margin-left: auto !important; margin-right: 0 !important;')
                            location = map.generic_layer(name='polygon',args=coordinates)
                            await map.initialized()
                            map.run_map_method('fitBounds', copy.deepcopy([coordinates[0][0], coordinates[0][2]]))

    async def select_in_search_results(e, page_selector, query, gdc, filtered_json, sender=None):
        on_topics_picked(e, sender=sender, is_page_selection=True)
        if sender.text == "Unselect" and e.value[0] in tree.selected_datasets:
            tree.selected_datasets.pop(e.value[0])   
        sender.text = "Unselect" if sender.text == "Select" else "Select"        
        #await update_search_results(page_selector, query, gdc, filtered_json)

    def clean_page():
        page.right_sidebar.clear()
        page.dataset_sidebar.clear()
        tree.features = {}
        tree.selected_topics = []
        tree.selected_datasets = {}

    async def scrape_topics_tree(gdc):
        with page.content_card:
            json = json_scrapes[gdc]
            ui.update()
            clean_page()
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

    def on_topics_picked(e,sender=None, is_page_selection=False):
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
        with page.dataset_sidebar:
            page.dataset_sidebar.clear()
            ui.label("Datasets:").style('font-weight: bold; font-size: 16px;').style('color:' + "#4A72C3" + ';')
            select_all_btn = ui.button('Select All', on_click=lambda e: select_all_datasets(e))
            added_datasets = []
            with ui.scroll_area().style('height: 75vh;'):
                for topic in topics:
                    for (key,features) in tree.features.items():
                        if topic[0:-2] in key:
                            for dataset in features:
                                if dataset['id'] not in added_datasets:
                                    added_datasets.append(dataset['id'])
                                else:
                                    continue
                                with ui.card().tight().style('width: 170px; max-width: 170px;'):
                                    ui.label(f"{dataset['id']}").classes("break-all").style('font-weight: bold; font-size: 14px; width: 170px; max-width: 170px; background-color: #f0f0f0;')
                                    select_btn = ui.button(f"Select")\
                                        .style('font-size:12px;width:170px;max-width:200px;min-width:80px;text-overflow:ellipsis;')\
                                        .on('click', lambda e, topic=topic, dataset_id=dataset['id']: select_dataset(e, topic, dataset_id))
                                    if is_page_selection:
                                        select_btn.run_method("click")
                                    ui.button(f"Show Metadata")\
                                        .style('font-size:12px;width:170px;max-width:200px;min-width:80px;text-overflow:ellipsis;')\
                                        .on('click', lambda e, dataset_id=dataset['id']: show_metadata(dataset_id))
    
    async def select_all_datasets(e):
                if e.sender.text == "Select All":
                    for child in page.dataset_sidebar.descendants():
                        if isinstance(child, ui.button) and child.text in ["Select"]:
                            child.run_method("click")
                else:
                    for child in page.dataset_sidebar.descendants():
                        if isinstance(child, ui.button) and child.text in ["Unselect"]:
                            child.run_method("click")
                e.sender.text = "Unselect All" if e.sender.text == "Select All" else "Select All"
                e.sender.set_background_color("#77AEE4" if e.sender.text == "Unselect All" else "primary")

    async def select_dataset(e, topic, dataset_id):
        e.sender.text = "Unselect" if e.sender.text == "Select" else "Select"
        e.sender.set_background_color("#77AEE4" if e.sender.text == "Unselect" else "primary")
        if topic not in tree.selected_datasets:
            tree.selected_datasets[topic] = []
        if dataset_id not in tree.selected_datasets[topic]:
            tree.selected_datasets[topic].append(dataset_id)
        else:
            tree.selected_datasets[topic].remove(dataset_id)
            if len(tree.selected_datasets[topic]) == 0:
                del tree.selected_datasets[topic]
        #print(tree.selected_datasets)
    
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
                    coordinates = copy.deepcopy(dataset['geometry']['coordinates'])
                    coordinates[0]= coordinates[0][:-1]
                    coordinates = [[(coord[1], coord[0]) for coord in coordinates[0]]]
                    map = ui.leaflet(center=coordinates[0][0], zoom=5)
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
