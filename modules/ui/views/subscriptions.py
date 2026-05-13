import json
import httpx
from nicegui import ui

from config import SUBSCRIPTION_MANAGER
from i18n import t
from views.shared import (
    _validate_target, _validate_filter,
    _build_filter, _try_parse_filter,
    DEFAULT_ACCEPTED_MEDIA_TYPES, _DATE_RE, _TIME_RE,
)


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
                                with ui.row().classes("gap-2"):
                                    async def _on_edit(
                                        _, s=sub_id, tpc=topic,
                                        pth=sub_data.get('save_path'), flt=filter_cfg,
                                    ):
                                        await open_edit(s, tpc, pth, flt)
                                    ui.button(
                                        t('btn.edit'), icon='edit'
                                    ).classes("subscription-action-btn").on('click', _on_edit)
                                    ui.button(
                                        t('btn.unsubscribe'), icon='remove_circle_outline'
                                    ).classes("subscription-action-btn").on(
                                        'click',
                                        lambda _, sid=sub_id: unsubscribe(sid),
                                    )

        async def open_edit(
            sub_id: str, topic: str, save_path: str | None, filter_cfg: dict
        ):
            async with httpx.AsyncClient() as client:
                resp = await client.get(f'{SUBSCRIPTION_MANAGER}/subscriptions/{sub_id}')
            if resp.status_code != 200:
                ui.notify(t('subscriptions.edit_load_error'), type='negative')
                return

            sub_full = resp.json()
            creds = sub_full.get('credentials') or {}
            original_auth_type = creds.get('type', 'none')
            current_username = creds.get('username', '')
            current_queue = sub_full.get('queue', 'small_files')

            # Decide rendering mode for filters
            parsed = _try_parse_filter(filter_cfg)
            use_controls = parsed is not None

            with ui.dialog() as dialog, ui.card().classes("manual-sub-card"):
                ui.label(t('subscriptions.edit_title')).classes("sidebar-title")
                ui.label(topic).classes('text-caption text-grey-6')

                ui.separator()

                target_input = ui.input(
                    label=t('manual.target_label'),
                    placeholder=t('sidebar.save_directory_hint'),
                    value=save_path or '',
                    validation=_validate_target,
                ).classes("directory-input")

                ui.separator()
                ui.label(t('sidebar.filters')).classes("sidebar-section-title")

                # Widgets that are only assigned in one branch; referenced in on_save
                filter_area = media_type_select = None
                north = south = east = west = None
                start_date = end_date = start_time = end_time = None

                if not use_controls:
                    ui.notify(t('subscriptions.filter_parse_warning'), type='warning')
                    filter_area = ui.textarea(
                        label=t('manual.filter_label'),
                        placeholder=t('manual.filter_hint'),
                        value=json.dumps(filter_cfg, indent=2) if filter_cfg else '',
                        validation=_validate_filter,
                    ).classes("directory-input filter-textarea")
                else:
                    if parsed['dataset_ids']:
                        with ui.expansion(
                            t('sidebar.datasets'), icon='dataset'
                        ).classes("filter-expansion"):
                            for did in parsed['dataset_ids']:
                                ui.label(did).classes('text-caption text-grey-6')

                    media_type_select = ui.select(
                        options=DEFAULT_ACCEPTED_MEDIA_TYPES,
                        label=t('sidebar.media_types'),
                        multiple=True,
                        value=parsed['media_types'] or None,
                    ).classes("filter-input")

                    with ui.expansion(t('sidebar.bbox'), icon="crop_square").classes(
                        "filter-expansion"
                    ):
                        with ui.grid(columns=2).classes("bbox-grid"):
                            north = ui.number(
                                label=t('sidebar.north'), min=-90, max=90,
                                value=parsed['north'],
                            ).classes("bbox-input")
                            east = ui.number(
                                label=t('sidebar.east'), min=-180, max=180,
                                value=parsed['east'],
                            ).classes("bbox-input")
                            south = ui.number(
                                label=t('sidebar.south'), min=-90, max=90,
                                value=parsed['south'],
                            ).classes("bbox-input")
                            west = ui.number(
                                label=t('sidebar.west'), min=-180, max=180,
                                value=parsed['west'],
                            ).classes("bbox-input")

                    with ui.expansion(t('sidebar.date_range'), icon="date_range").classes(
                        "filter-expansion"
                    ):
                        start_date = ui.input(
                            label=t('sidebar.start_date'),
                            placeholder=t('sidebar.start_date_hint'),
                            value=parsed['start_date'] or '',
                            validation=lambda v: None if not v or _DATE_RE.match(v) else t('validation.date_format'),
                        ).classes("filter-input")
                        end_date = ui.input(
                            label=t('sidebar.end_date'),
                            placeholder=t('sidebar.start_date_hint'),
                            value=parsed['end_date'] or '',
                            validation=lambda v: None if not v or _DATE_RE.match(v) else t('validation.date_format'),
                        ).classes("filter-input")
                        start_time = ui.input(
                            label=t('sidebar.start_time'),
                            placeholder=t('sidebar.time_hint'),
                            value=parsed['start_time'] or '',
                            validation=lambda v: None if not v or _TIME_RE.match(v) else t('validation.time_format'),
                        ).classes("filter-input")
                        end_time = ui.input(
                            label=t('sidebar.end_time'),
                            placeholder=t('sidebar.time_hint'),
                            value=parsed['end_time'] or '',
                            validation=lambda v: None if not v or _TIME_RE.match(v) else t('validation.time_format'),
                        ).classes("filter-input")

                ui.separator()
                ui.label(t('sidebar.queue')).classes("sidebar-section-title")
                queue_radio = ui.radio(
                    {
                        'high_priority': t('sidebar.queue_high'),
                        'small_files':   t('sidebar.queue_small'),
                        'large_files':   t('sidebar.queue_large'),
                    },
                    value=current_queue,
                ).props('inline')

                ui.separator()
                ui.label(t('sidebar.auth')).classes("sidebar-section-title")
                auth_type = ui.radio(
                    {
                        'none':   t('sidebar.auth_none'),
                        'basic':  t('sidebar.auth_basic'),
                        'bearer': t('sidebar.auth_bearer'),
                    },
                    value=original_auth_type,
                ).props('inline')
                ui.label(t('subscriptions.credentials_note')).classes(
                    'text-caption text-grey-6'
                )

                def _req(v):
                    return (
                        t('validation.auth_credentials_required')
                        if not (v or '').strip() else None
                    )

                with ui.column().bind_visibility_from(
                    auth_type, 'value', backward=lambda v: v == 'basic'
                ):
                    username_input = ui.input(
                        label=t('sidebar.auth_username'),
                        value=current_username,
                        validation=_req,
                    ).classes("directory-input")
                    password_input = ui.input(
                        label=t('sidebar.auth_password'),
                        password=True,
                        password_toggle_button=True,
                    ).classes("directory-input")

                with ui.column().bind_visibility_from(
                    auth_type, 'value', backward=lambda v: v == 'bearer'
                ):
                    token_input = ui.input(
                        label=t('sidebar.auth_token'),
                        password=True,
                        password_toggle_button=True,
                    ).classes("directory-input")

                async def on_save():
                    target_input.validate()
                    if target_input.error:
                        ui.notify(t('validation.fix_errors'), type='warning')
                        return

                    if use_controls:
                        filter_result = _build_filter(
                            [], media_type_select,
                            north, south, east, west,
                            start_date, end_date, start_time, end_time,
                            {}, {},
                        )
                        if filter_result is None:
                            return  # date/time validation error already notified
                    else:
                        filter_area.validate()
                        if filter_area.error:
                            ui.notify(t('validation.fix_errors'), type='warning')
                            return
                        raw = (filter_area.value or '').strip()
                        filter_result = json.loads(raw) if raw and raw != '{}' else {}

                    new_type = auth_type.value
                    include_credentials = False
                    credentials_value = None

                    if new_type == 'none':
                        include_credentials = True
                    elif new_type == 'basic':
                        p = (password_input.value or '').strip()
                        u = (username_input.value or '').strip()
                        if p:
                            if not u:
                                ui.notify(
                                    t('validation.auth_credentials_required'), type='warning'
                                )
                                return
                            credentials_value = {'type': 'basic', 'username': u, 'password': p}
                            include_credentials = True
                        elif new_type != original_auth_type:
                            ui.notify(
                                t('validation.auth_credentials_required'), type='warning'
                            )
                            return
                    elif new_type == 'bearer':
                        tkn = (token_input.value or '').strip()
                        if tkn:
                            credentials_value = {'type': 'bearer', 'token': tkn}
                            include_credentials = True
                        elif new_type != original_auth_type:
                            ui.notify(
                                t('validation.auth_credentials_required'), type='warning'
                            )
                            return

                    payload: dict = {
                        'target': target_input.value.strip() or './',
                        'filter': filter_result,
                        'queue': queue_radio.value or 'small_files',
                    }
                    if include_credentials:
                        payload['credentials'] = credentials_value

                    dialog.close()
                    async with httpx.AsyncClient() as client:
                        await client.put(
                            f'{SUBSCRIPTION_MANAGER}/subscriptions/{sub_id}',
                            json=payload,
                        )
                    await load_subscriptions()

                with ui.row().classes("justify-end gap-2"):
                    ui.button(t('btn.cancel'), icon='close').props('flat').on(
                        'click', dialog.close
                    )
                    ui.button(t('btn.confirm'), icon='check_circle').props(
                        'color=primary'
                    ).on('click', on_save)

            dialog.open()

        async def unsubscribe(sub_id: str):
            async with httpx.AsyncClient() as client:
                await client.delete(f'{SUBSCRIPTION_MANAGER}/subscriptions/{sub_id}')
            await load_subscriptions()

        reload_btn.on('click', load_subscriptions)
        ui.timer(0, load_subscriptions, once=True)
