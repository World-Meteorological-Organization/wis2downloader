"""English strings — source of truth for all translations."""

STRINGS: dict[str, str] = {
    # ------------------------------------------------------------------ #
    # Navigation                                                           #
    # ------------------------------------------------------------------ #
    'nav.dashboard':  'Dashboard',
    'nav.catalogue':  'Catalogue View',
    'nav.tree':       'Tree View',
    'nav.manual':     'Manual Subscribe',
    'nav.manage':     'Manage Subscriptions',
    'nav.settings':   'Settings',
    'nav.help':       'Help',

    # ------------------------------------------------------------------ #
    # Buttons                                                              #
    # ------------------------------------------------------------------ #
    'btn.subscribe':        'Subscribe',
    'btn.confirm':          'Confirm',
    'btn.cancel':           'Cancel',
    'btn.close':            'Close',
    'btn.filter':           'Filter',
    'btn.reload':           'Reload Subscriptions',
    'btn.unsubscribe':      'Unsubscribe',
    'btn.refresh_gdc':      'Refresh GDC data',
    'btn.show_metadata':    'Show Metadata',
    'btn.view_license':     'View License',
    'btn.select':           'Select',
    'btn.unselect':         'Unselect',
    'btn.select_all':       'Select / deselect all',
    'btn.toggle_nav':       'Toggle navigation',

    # ------------------------------------------------------------------ #
    # Subscription sidebar (shared)                                        #
    # ------------------------------------------------------------------ #
    'sidebar.selected_topics':       'Selected Topics',
    'sidebar.save_directory':        'Save directory',
    'sidebar.save_directory_hint':   './',
    'sidebar.filters':               'Filters',
    'sidebar.dataset':               'Dataset',
    'sidebar.datasets':              'Datasets',
    'sidebar.media_types':           'Media types',
    'sidebar.bbox':                  'Bounding box',
    'sidebar.north':                 'North',
    'sidebar.east':                  'East',
    'sidebar.south':                 'South',
    'sidebar.west':                  'West',
    'sidebar.date_range':            'Date & time range',
    'sidebar.start_date':            'Start date',
    'sidebar.end_date':              'End date',
    'sidebar.start_date_hint':       'YYYY-MM-DD',
    'sidebar.start_time':            'Start time (UTC)',
    'sidebar.end_time':              'End time (UTC)',
    'sidebar.time_hint':             'HH:MM',
    'sidebar.custom_filters':        'Custom filters',

    # ------------------------------------------------------------------ #
    # Validation messages                                                  #
    # ------------------------------------------------------------------ #
    'validation.date_format':        'Use YYYY-MM-DD',
    'validation.time_format':        'Use HH:MM (24-hour)',
    'validation.date_time_errors':   'Fix date/time format errors before subscribing.',
    'validation.fix_errors':         'Fix validation errors before subscribing.',

    # ------------------------------------------------------------------ #
    # Confirm subscription dialog                                          #
    # ------------------------------------------------------------------ #
    'dialog.confirm_title': 'Confirm Subscription',

    # ------------------------------------------------------------------ #
    # Metadata dialog                                                      #
    # ------------------------------------------------------------------ #
    'metadata.id':            'ID: {id}',
    'metadata.title':         'Title: {title}',
    'metadata.description':   'Description: {description}',
    'metadata.keywords':      'Keywords:',
    'metadata.not_available': 'Metadata not available for: {id}',

    # ------------------------------------------------------------------ #
    # Catalogue view                                                       #
    # ------------------------------------------------------------------ #
    'catalogue.title':              'Catalogue View',
    'catalogue.not_loaded':         'Catalogue data not loaded',
    'catalogue.not_loaded_msg':     (
        'GDC data is still being fetched. Try again in a moment, '
        'or visit Settings to trigger a manual refresh.'
    ),
    'catalogue.search_label':       'Free text search:',
    'catalogue.search_hint':        'e.g. surface observations',
    'catalogue.data_policy':        'Data Policy',
    'catalogue.keywords_label':     'Keywords (comma-separated)',
    'catalogue.bbox_label':         'Bounding box:',
    'catalogue.bbox_spatial_rel':   'Spatial relationship:',
    'catalogue.bbox_intersects':    'Intersects',
    'catalogue.bbox_within':        'Within',
    'catalogue.no_results':         'No results found.',
    'catalogue.page':               'Page',
    'catalogue.discrepancy':        'Record content differs between catalogues',

    # ------------------------------------------------------------------ #
    # Tree view                                                            #
    # ------------------------------------------------------------------ #
    'tree.title':         'Tree View',
    'tree.filter_label':  'Filter topics',
    'tree.loading':       'Loading\u2026',

    # ------------------------------------------------------------------ #
    # Manage Subscriptions view                                            #
    # ------------------------------------------------------------------ #
    'subscriptions.folder':        'Folder: {path}',
    'subscriptions.id':            'ID: {id}',
    'subscriptions.filter_default': 'Filter: default',
    'subscriptions.filter_named':  'Filter: {name}',
    'subscriptions.filter_custom': 'Filter: custom',

    # ------------------------------------------------------------------ #
    # Settings view                                                        #
    # ------------------------------------------------------------------ #
    'settings.title':       'Settings',
    'settings.gdc_section': 'Global Discovery Catalogues',
    'settings.gdc_desc': (
        'Records are fetched from all three GDCs at startup and merged. '
        'Results are cached in Redis for 6 hours.'
    ),
    'settings.records':     '{name}: {count} records',
    'settings.not_loaded':  '{name}: not loaded',

    # ------------------------------------------------------------------ #
    # Manual Subscribe view                                                #
    # ------------------------------------------------------------------ #
    'manual.title':       'Manual Subscription',
    'manual.description': 'Enter a WIS2 topic, save directory, and optional filter.',
    'manual.topic_label': 'Topic',
    'manual.topic_hint':  'cache/a/wis2/+/data/core/weather/surface-based-observations/#',
    'manual.target_label': 'Save directory',
    'manual.filter_label': 'Filter (JSON)',
    'manual.filter_hint': (
        'Leave empty to use the default filter, or paste a filter object:\n'
        '{\n'
        '  "rules": [\n'
        '    {"id": "accept-all", "order": 1,\n'
        '     "match": {"always": true}, "action": "accept"}\n'
        '  ]\n'
        '}'
    ),

    # Validation
    'manual.val.topic_required':    'Topic is required',
    'manual.val.topic_format': (
        'Must match (cache|origin)/a/wis2/{centre}/data/\u2026'
        ' \u2014 use + for single-level wildcards, # only at the end'
    ),
    'manual.val.path_traversal':    'Path traversal (..) not allowed',
    'manual.val.path_absolute':     'Must be a relative path (no leading /)',
    'manual.val.json_invalid':      'Invalid JSON: {msg} (line {lineno}, col {colno})',
    'manual.val.not_object':        'Filter must be a JSON object { \u2026 }',
    'manual.val.missing_rules':     'Filter must have a "rules" key',
    'manual.val.rules_not_array':   '"rules" must be an array [ \u2026 ]',
    'manual.val.rule_not_object':   'Rule {i}: must be an object',
    'manual.val.rule_missing_field': 'Rule {i}: missing required field "{field}"',
    'manual.val.rule_wrong_type':   'Rule {i}: "{field}" must be a {type_name}',
    'manual.val.rule_bad_action':   'Rule {i}: "action" must be one of: accept, reject, continue',

    # ------------------------------------------------------------------ #
    # Footer                                                               #
    # ------------------------------------------------------------------ #
    'footer.copyright': '\u00a9 2026 World Meteorological Organization',

    # ------------------------------------------------------------------ #
    # Accessibility / ARIA                                                 #
    # ------------------------------------------------------------------ #
    'aria.toggle_nav': 'Toggle navigation',
    'aria.discrepancy': 'Record content differs between catalogues',
}
