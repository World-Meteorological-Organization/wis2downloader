from cProfile import label
import os
from xmlrpc import client
import httpx
from nicegui import app, ui, binding, context
import json

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

    tree = Tree(value= 5)

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
            tree.value = 5
            tree.selected_topics = []
            page.left_sidebar.clear()
            page.right_sidebar.clear()
            label = ui.label("Please select a source GDC.").style('margin-left: 10px; font-weight: bold;').style('color: black;')
            if e.value == 'tree':
                url = radio1 = ui.radio({"https://gdc.wis.cma.cn":'CMA', "https://wis2.dwd.de/gdc":'DWD', "https://wis2-gdc.weather.gc.ca":"ECCC" }).props('inline').on('update:model-value', lambda e: scrap_topics_tree(url.value))
            else:
                url = radio1 = ui.radio({"https://gdc.wis.cma.cn":'CMA', "https://wis2.dwd.de/gdc":'DWD', "https://wis2-gdc.weather.gc.ca":"ECCC" }).props('inline').on('update:model-value', lambda e: scrap_topics_page(url.value))

    async def scrap_topics_page(url):
        with page.content_card:
            with ui.row():
                search_input = ui.input(label='Search topics').style('width: 100%;')
                search_button = ui.button('Search').style('margin-left: 10px;').on('click', lambda: perform_search(search_input.value,url))
    
    async def perform_search(query, url):
        page.right_sidebar.clear()
        page.left_sidebar.clear()
        async with httpx.AsyncClient() as client:
            with page.content_card:
                for child in page.content_card.descendants():
                    print("Deleting child:", child)
                    if isinstance(child,ui.column):
                        child.delete()
                        ui.update()
                with ui.column() as results_column:
                    results_column.set_visibility(True)
                    response = await client.get(str(url) + f'/collections/wis2-discovery-metadata/items?limit=10&f=json&q={query}')
                    json = response.json()
                    tree.features = {}
                    tree.selected_topics = []
                    tree.value = 5
                    for item in json['features']:
                        for link in item['links']:
                            if "channel" in link and link["channel"].startswith('cache/'):
                                if link["channel"] not in tree.features:
                                    tree.features[link["channel"]] = []
                                tree.features[link["channel"]].append(item)
                                break  
                    total_matched = json["numberMatched"]
                    num_pages = (total_matched // 10) + (1 if total_matched % 10 > 0 else 0)
                    page_selector = ui.select(options=[str(i+1) for i in range(num_pages)], label='Page', value='1', with_input=True).style('width: 10vh;').on('update:model-value', lambda e: update_search_results(page_selector, query, url, results_column))
                    await update_search_results(page_selector, query, url, results_column)

    async def update_search_results(page_selector, query, url, results_column):
        print(tree.features)
        print(tree.selected_topics)
        with results_column:
            page_number = int(page_selector.value)
            num_pages = len(page_selector.options)
            results_column.clear()
            page_selector = ui.select(options=[str(i+1) for i in range(num_pages)], label='Page', value=str(page_number), with_input=True).style('width: 10vh;').on('update:model-value', lambda e: update_search_results(page_selector, query, url, results_column))
            async with httpx.AsyncClient() as client:
                offset = (page_number - 1) * 10
                response = await client.get(str(url) + f'/collections/wis2-discovery-metadata/items?limit=10&f=json&q={query}&offset={offset}')
                json = response.json()
                ui.label(f"Number Returned: {json['numberReturned']}")
                tree_list = []
                i = 0
                for item in json['features']:
                    with ui.card().tight().style('margin-top: 10px; max-width: 60vh'):
                        ui.label(f"ID: {item['id']}").style('font-weight: bold;')
                        ui.label(f"Title: {item['properties'].get('title', 'N/A')}").style('font-weight: bold;')
                        ui.label(f"Description: {item['properties'].get('description', 'N/A')}").style('font-weight: bold;')
                        with ui.row():
                            ui.button("Show Metadata").on('click', lambda e, dataset_id=item['id']: show_metadata(dataset_id))       
                            for item_link in item['links']:
                                if "channel" in item_link and item_link["channel"].startswith('cache/'):
                                    tree_list.append(Tree([item_link['channel']]))
                                    i+=1
                                    selector = ui.button("Select").on('click', lambda e, tree=tree_list[i-1]: on_topics_picked(tree,sender=e.sender))
                                    if item_link['channel'] in tree.selected_topics:
                                        selector.text = "Deselect"
                                    break   

    async def scrap_topics_tree(url):
        async with httpx.AsyncClient() as client:
            with page.content_card:
                label = ui.label('Loading...').style('margin-left: 10px; font-weight: bold;').style('color: black;')
                response = await client.get(str(url) + '/collections/wis2-discovery-metadata/items?limit=2000&f=json')
                json = response.json()
                ui.update()
                tree.features = {}
                dicc = {}
                # for item in json['features']:
                #     if "wmo:topicHierarchy" in item['properties']:
                #         print("Processing topic:", item['properties']['wmo:topicHierarchy'])
                #         dicc = put_in_dicc(dicc, item['properties']['wmo:topicHierarchy'], item['properties']['wmo:topicHierarchy'])
                for item in json['features']:
                    # if len(item['links']) > 0 and "channel" in item['links'][0] and item['links'][0]["channel"].startswith('cache/'):
                    for link in item['links']:
                        if "channel" in link and link["channel"].startswith('cache/'):
                            if link["channel"] not in tree.features:
                                tree.features[link["channel"]] = []
                            tree.features[link["channel"]].append(item)
                            dicc = put_in_dicc(dicc, link["channel"], link["channel"])
                            break  
                print("deleting old tree")
                if not isinstance(tree.value, int):
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
                if sender is not None:
                    sender.text = "Deselect"
            else:
                tree.selected_topics.remove(e.value[0])
                if sender is not None:
                    sender.text = "Select"
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
            if directory == '':
                directory = 'data'
            for topic in topics:
                payload = {
                    "topic": topic,
                    "target": directory
                }
                print("Subscribing to topic:", topic)
                print("With payload:", payload)
                response = await client.post('http://172.18.0.7:5001/subscriptions', json=payload)

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
                ui.label(f"Description: {dataset['properties'].get('description', 'N/A')}").style('font-weight: bold;')
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
                    # map.run_map_method('fitBounds', [coordinates[0][0], coordinates[0][2]])
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
            response = await client.get('http://172.18.0.7:5001/subscriptions')
            page.subscriptions = response.json()
            print("Loaded subscriptions:", page.subscriptions)
            for element in page.content.descendants():
                if element is not reload and element is not page.content:
                    element.delete()
            with page.content:
                scroll_area = ui.scroll_area().style('height: 90vh;') 
            with scroll_area:
                for broker in page.subscriptions:
                    for (sub) in page.subscriptions[broker]:
                        with ui.row():
                            ui.label(f"Topic: {sub}").style('margin-left: 10px; font-weight: bold;').style('color: black;')
                            ui.label(f"Folder: {page.subscriptions[broker][sub]['target']}").style('margin-left: 10px; font-weight: bold;').style('color: black;')
                            ui.button("Unsubscribe").style('margin-left: 10px;').on('click', lambda e: unsubscribe(e.sender.parent_slot.children[0].text.replace('Topic: ', '')))
    
    async def unsubscribe(sub_id):
        async with httpx.AsyncClient() as client:
            print("Unsubscribing from:", sub_id)
            sub_id = sub_id.replace('#', '%23')
            response = await client.delete(f'http://172.18.0.7:5001/subscriptions/{sub_id}')
            await load_subscriptions()


ui.run()
