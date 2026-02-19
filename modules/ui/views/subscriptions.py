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
                subscriptions = response.json()
            with subscriptions_col:
                scroll_area = ui.scroll_area().classes("subscriptions-scroll")
            with scroll_area:
                for sub in subscriptions:
                    with ui.card():
                        with ui.card_section():
                            ui.label(sub).classes('text-subtitle2')
                            ui.label(
                                f"Folder: {subscriptions[sub]['save_path']}"
                            ).classes('text-body2 text-grey-7')
                            ui.button("Unsubscribe", icon='remove_circle_outline').classes("subscription-action-btn").on(
                                'click',
                                lambda ev: unsubscribe(
                                    ev.sender.parent_slot.children[0].text.replace('Topic: ', '')
                                ),
                            )

        async def unsubscribe(sub_id):
            async with httpx.AsyncClient() as client:
                sub_id = sub_id.replace('#', '%23').replace('+', '%2B')
                await client.delete(f'{SUBSCRIPTION_MANAGER}/subscriptions/{sub_id}')
            await load_subscriptions()

        reload_btn.on('click', load_subscriptions)
        ui.timer(0, load_subscriptions, once=True)
