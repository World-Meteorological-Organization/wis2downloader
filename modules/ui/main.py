from cProfile import label
import os
from xmlrpc import client
import httpx
from nicegui import app, ui, binding, context
import json
import copy
from shared import setup_logging

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
            try:
                response = client.get(str(url[0]) + f'/collections/wis2-discovery-metadata/items?limit=2000&f=json', timeout=5)
            except Exception as e:
                LOGGER.error(f"Error fetching data from {url[0]}: {e}")
                response = None
                json_scrapes[url[1]] = {}
                continue
            json_scrape = response.json()
            json_scrapes[url[1]] = json_scrape
scrape_all_task = ui.run( scrape_all())

SUBSCRIPTION_MANAGER = "http://subscription-manager:5001"
app.colors(base_100="#FFFFFF",
           base_200="#5D8FCF",
           base_300="#77AEE4",
           base_400="#206AAA",
           )

@ui.page('/')
def home_page():
    context.client.content.classes('h-[100vh]')

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

    with ui.element("div").classes("flex w-full h-screen absolute"):
            # MenuBar
        page.home = ui.element("div").classes("flex flex-col max-w-xs bg-base-400 p-4 items-center justify-start gap-4")
        with page.home:
            ui.button(icon="home", text="GDC Subscription", color="base-100").props("flat round").on('click', lambda: ui.navigate.to('/'))
            ui.button(icon="logout", text="Unsubscribe", color="base-100").props("flat round").on('click', lambda: ui.navigate.to('/unsubscribe'))

            # Left Sidebar
        page.left_sidebar = ui.element("div").classes("w-[20%] max-w-sm bg-base-200 p-4")
        with page.left_sidebar:
            pass

            # Content
        page.content = ui.element("div").classes("grow bg-base-100 p-4")
        with page.content:
            view_label = ui.label('Please select a type of display for the topics:').style('font-weight: bold; font-size: 16px;').style('color:' + "#4A72C3" + ';')
            view = ui.radio({'tree':'Tree view', 'page':'Text search'}).props('inline').on('update:model-value', lambda e: on_view_changed(view))

        # Right Sidebar
        page.right_sidebar = ui.element("div").classes("w-[20%] max-w-sm bg-base-200 p-4")
        with page.right_sidebar:
            pass

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
            coordinates = feature['geometry']['coordinates'][0]
            if isinstance(coordinates, list) and isinstance(coordinates[0], list):
                pass
            else:
                return False
            lons = [coord[0] for coord in coordinates]
            lats = [coord[1] for coord in coordinates]
            min_lon, max_lon = min(lons), max(lons)
            min_lat, max_lat = min(lats), max(lats)
            if isinstance(min_lon,list) or isinstance(max_lon,list) or isinstance(min_lat,list) or isinstance(max_lat,list):
                return False 
            if max_lon >= bbox[1] and min_lon <= bbox[2] and max_lat >= bbox[3] and min_lat <= bbox[0]:
                return True
            return False
        return False
    
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
            print(len(features))
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
            ui.label("Selected Topics:").style('font-weight: bold; font-size: 16px;').style('color:' + "#EDEFF3" + ';')
            for topic in topics:
                ui.label(topic).style('margin-left: 10px; font-weight: bold;').style('color: white;').style('background-color: #77AEE4; padding: 2px; border-radius: 3px;')
            directory = ui.textarea("Directory to save datasets(default: data):").style('margin-top: 10px; width: 100%;')
            submit = ui.button("Submit").style('margin-top: 10px;').on('click', lambda: subscribe_to_topics(topics, directory.value))
        with page.left_sidebar:
            page.left_sidebar.clear()
            ui.label("Datasets:").style('font-weight: bold; font-size: 16px;').style('color:' + "#EDEFF3" + ';')
            with ui.scroll_area().style('height: 90vh;'):
                for topic in topics:
                        for (key,features) in tree.features.items():
                            if topic[0:-2] in key:
                                for dataset in features:
                                    ui.button(f"{dataset['id']}").style('font-size:12px;width:80%').on('click', lambda e: show_metadata(e.sender.text))
    
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
        page.right_sidebar = ui.element("div").classes("w-[20%] max-w-xsg-base-200 p-4")
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
