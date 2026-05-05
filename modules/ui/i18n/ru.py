"""Russian translations.

NOTE: Machine-generated — must be reviewed by a native Russian speaker,
especially WMO/meteorological terms (WIS2, BUFR, GRIB, etc.).
"""

STRINGS: dict[str, str] = {
    # ------------------------------------------------------------------ #
    # Navigation                                                           #
    # ------------------------------------------------------------------ #
    'nav.dashboard':  'Панель управления',
    'nav.catalogue':  'Просмотр каталога',
    'nav.tree':       'Древовидная структура',
    'nav.manual':     'Ручная подписка',
    'nav.manage':     'Управление подписками',
    'nav.settings':   'Настройки',
    'nav.help':       'Справка',

    # ------------------------------------------------------------------ #
    # Buttons                                                              #
    # ------------------------------------------------------------------ #
    'btn.subscribe':        'Подписаться',
    'btn.confirm':          'Подтвердить',
    'btn.cancel':           'Отмена',
    'btn.close':            'Закрыть',
    'btn.filter':           'Фильтр',
    'btn.reload':           'Обновить подписки',
    'btn.unsubscribe':      'Отписаться',
    'btn.refresh_gdc':      'Обновить данные GDC',
    'btn.show_metadata':    'Показать метаданные',
    'btn.view_license':     'Просмотр лицензии',
    'btn.accept':           'Принять',
    'btn.select':           'Выбрать',
    'btn.unselect':         'Снять выбор',
    'btn.select_all':       'Выбрать / снять выбор всех',
    'btn.toggle_nav':       'Переключить навигацию',

    # ------------------------------------------------------------------ #
    # Subscription sidebar (shared)                                        #
    # ------------------------------------------------------------------ #
    'sidebar.selected_topics':       'Выбранные темы',
    'sidebar.save_directory':        'Каталог сохранения',
    'sidebar.save_directory_hint':   './',
    'sidebar.filters':               'Фильтры',
    'sidebar.dataset':               'Набор данных',
    'sidebar.datasets':              'Наборы данных',
    'sidebar.media_types':           'Типы медиа',
    'sidebar.bbox':                  'Географический охват',
    'sidebar.north':                 'Север',
    'sidebar.east':                  'Восток',
    'sidebar.south':                 'Юг',
    'sidebar.west':                  'Запад',
    'sidebar.date_range':            'Диапазон дат и времени',
    'sidebar.start_date':            'Дата начала',
    'sidebar.end_date':              'Дата окончания',
    'sidebar.start_date_hint':       'ГГГГ-ММ-ДД',
    'sidebar.start_time':            'Время начала (UTC)',
    'sidebar.end_time':              'Время окончания (UTC)',
    'sidebar.time_hint':             'ЧЧ:ММ',
    'sidebar.custom_filters':        'Пользовательские фильтры',

    # ------------------------------------------------------------------ #
    # Validation messages                                                  #
    # ------------------------------------------------------------------ #
    'validation.date_format':        'Используйте формат ГГГГ-ММ-ДД',
    'validation.time_format':        'Используйте формат ЧЧ:ММ (24 часа)',
    'validation.date_time_errors':   'Исправьте ошибки формата даты/времени перед подпиской.',
    'validation.fix_errors':         'Исправьте ошибки валидации перед подпиской.',

    # ------------------------------------------------------------------ #
    # Confirm subscription dialog                                          #
    # ------------------------------------------------------------------ #
    'dialog.confirm_title':  'Подтвердить подписку',
    'dialog.license_title':  'Ознакомиться с лицензией',
    'dialog.license_msg':    'Этот набор данных имеет лицензию. Пожалуйста, ознакомьтесь с ней перед подпиской.',

    # ------------------------------------------------------------------ #
    # Metadata dialog                                                      #
    # ------------------------------------------------------------------ #
    'metadata.id':            'ID: {id}',
    'metadata.title':         'Заголовок: {title}',
    'metadata.description':   'Описание: {description}',
    'metadata.keywords':      'Ключевые слова:',
    'metadata.not_available': 'Метаданные недоступны для: {id}',

    # ------------------------------------------------------------------ #
    # Catalogue view                                                       #
    # ------------------------------------------------------------------ #
    'catalogue.title':              'Вид каталога',
    'catalogue.not_loaded':         'Данные каталога не загружены',
    'catalogue.not_loaded_msg':     (
        'Данные GDC ещё загружаются. Попробуйте снова через момент '
        'или перейдите в Настройки для ручного обновления.'
    ),
    'catalogue.search_label':       'Поиск по тексту:',
    'catalogue.search_hint':        'напр. наземные наблюдения',
    'catalogue.data_policy':        'Политика данных',
    'catalogue.keywords_label':     'Ключевые слова (через запятую)',
    'catalogue.bbox_label':         'Географический охват:',
    'catalogue.bbox_spatial_rel':   'Пространственное соотношение:',
    'catalogue.bbox_intersects':    'Пересекает',
    'catalogue.bbox_within':        'Внутри',
    'catalogue.no_results':         'Результаты не найдены.',
    'catalogue.page':               'Страница',
    'catalogue.discrepancy':        'Содержимое записи различается между каталогами',

    # ------------------------------------------------------------------ #
    # Tree view                                                            #
    # ------------------------------------------------------------------ #
    'tree.title':         'Древовидный вид',
    'tree.filter_label':  'Фильтр тем',
    'tree.loading':       'Загрузка\u2026',

    # ------------------------------------------------------------------ #
    # Manage Subscriptions view                                            #
    # ------------------------------------------------------------------ #
    'subscriptions.folder':        'Папка: {path}',
    'subscriptions.id':            'ID: {id}',
    'subscriptions.filter_default': 'Фильтр: по умолчанию',
    'subscriptions.filter_named':  'Фильтр: {name}',
    'subscriptions.filter_custom': 'Фильтр: пользовательский',

    # ------------------------------------------------------------------ #
    # Settings view                                                        #
    # ------------------------------------------------------------------ #
    'settings.title':       'Настройки',
    'settings.gdc_section': 'Глобальные каталоги обнаружения',
    'settings.gdc_desc': (
        'Записи загружаются из всех трёх GDC при запуске и объединяются. '
        'Результаты кэшируются в Redis на 6 часов.'
    ),
    'settings.records':     '{name}: {count} записей',
    'settings.not_loaded':  '{name}: не загружен',

    # ------------------------------------------------------------------ #
    # Manual Subscribe view                                                #
    # ------------------------------------------------------------------ #
    'manual.title':       'Ручная подписка',
    'manual.description': 'Введите тему WIS2, каталог сохранения и необязательный фильтр.',
    'manual.topic_label': 'Тема',
    'manual.topic_hint':  'cache/a/wis2/+/data/core/weather/surface-based-observations/#',
    'manual.target_label': 'Каталог сохранения',
    'manual.filter_label': 'Фильтр (JSON)',
    'manual.filter_hint': (
        'Оставьте пустым для использования фильтра по умолчанию или вставьте объект фильтра:\n'
        '{\n'
        '  "rules": [\n'
        '    {"id": "accept-all", "order": 1,\n'
        '     "match": {"always": true}, "action": "accept"}\n'
        '  ]\n'
        '}'
    ),

    # Validation
    'manual.val.topic_required':    'Тема обязательна',
    'manual.val.topic_format': (
        'Должно соответствовать (cache|origin)/a/wis2/{centre}/data/\u2026'
        ' \u2014 используйте + для одноуровневых подстановочных знаков, # только в конце'
    ),
    'manual.val.path_traversal':    'Обход пути (..) не разрешён',
    'manual.val.path_absolute':     'Должен быть относительным путём (без ведущего /)',
    'manual.val.json_invalid':      'Неверный JSON: {msg} (строка {lineno}, столбец {colno})',
    'manual.val.not_object':        'Фильтр должен быть объектом JSON { \u2026 }',
    'manual.val.missing_rules':     'Фильтр должен содержать ключ "rules"',
    'manual.val.rules_not_array':   '"rules" должен быть массивом [ \u2026 ]',
    'manual.val.rule_not_object':   'Правило {i}: должно быть объектом',
    'manual.val.rule_missing_field': 'Правило {i}: отсутствует обязательное поле "{field}"',
    'manual.val.rule_wrong_type':   'Правило {i}: "{field}" должно быть типа {type_name}',
    'manual.val.rule_bad_action':   'Правило {i}: "action" должно быть одним из: accept, reject, continue',

    # ------------------------------------------------------------------ #
    # Footer                                                               #
    # ------------------------------------------------------------------ #
    'footer.copyright': '\u00a9 2026 Всемирная метеорологическая организация',

    # ------------------------------------------------------------------ #
    # Accessibility / ARIA                                                 #
    # ------------------------------------------------------------------ #
    'aria.toggle_nav': 'Переключить навигацию',
    'aria.discrepancy': 'Содержимое записи различается между каталогами',
}
