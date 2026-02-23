import httpx
from nicegui import ui

from config import SUBSCRIPTION_MANAGER


def render(container):
    with container:
        reload_btn = ui.button("Reload Subscriptions").classes("reload-btn")
        with ui.column() as subscriptions_col:
            pass

        async def load_subscriptions():
            subscriptions_col.clear()
            async with httpx.AsyncClient() as client:
                response = await client.get(f'{SUBSCRIPTION_MANAGER}/subscriptions')
                # response shape: {topic: {sub_id: {save_path, filter}}}
                by_topic = response.json()
            with subscriptions_col:
                scroll_area = ui.scroll_area().classes("subscriptions-scroll")
            with scroll_area:
                for topic, subs in by_topic.items():
                    for sub_id, sub_data in subs.items():
                        with ui.card():
                            with ui.card_section():
                                ui.label(topic).classes('text-subtitle2')
                                ui.label(
                                    f"Folder: {sub_data.get('save_path') or '/'}"
                                ).classes('text-body2 text-grey-7')
                                ui.button(
                                    "Unsubscribe", icon='remove_circle_outline'
                                ).classes("subscription-action-btn").on(
                                    'click',
                                    lambda _, sid=sub_id: unsubscribe(sid),
                                )

        async def unsubscribe(sub_id: str):
            async with httpx.AsyncClient() as client:
                await client.delete(f'{SUBSCRIPTION_MANAGER}/subscriptions/{sub_id}')
            await load_subscriptions()

        reload_btn.on('click', load_subscriptions)
        ui.timer(0, load_subscriptions, once=True)
