import httpx
from nicegui import ui

from config import SUBSCRIPTION_MANAGER
from i18n import t


def render(container):
    with container:
        reload_btn = ui.button(t('btn.reload')).classes("reload-btn")
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
                        filter_cfg = sub_data.get('filter') or {}
                        filter_name = filter_cfg.get('name') if filter_cfg else None
                        if filter_name:
                            filter_label = t('subscriptions.filter_named', name=filter_name)
                        elif filter_cfg.get('rules'):
                            filter_label = t('subscriptions.filter_custom')
                        else:
                            filter_label = t('subscriptions.filter_default')
                        with ui.card():
                            with ui.card_section():
                                ui.label(topic).classes('text-subtitle2')
                                ui.label(
                                    t('subscriptions.folder', path=sub_data.get('save_path') or '/')
                                ).classes('text-body2 text-grey-7')
                                ui.label(
                                    t('subscriptions.id', id=sub_id)
                                ).classes('text-caption text-grey-6')
                                ui.label(filter_label).classes('text-body2 text-grey-7')
                                ui.button(
                                    t('btn.unsubscribe'), icon='remove_circle_outline'
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
