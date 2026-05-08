"""Spanish translations.

"""

STRINGS: dict[str, str] = {
    # ------------------------------------------------------------------ #
    # Navigation                                                           #
    # ------------------------------------------------------------------ #
    'nav.dashboard':  'Panel de control',
    'nav.catalogue':  'Vista del catálogo',
    'nav.tree':       'Vista de árbol',
    'nav.manual':     'Suscripción manual',
    'nav.manage':     'Gestionar suscripciones',
    'nav.settings':   'Configuración',
    'nav.help':       'Ayuda',

    # ------------------------------------------------------------------ #
    # Buttons                                                              #
    # ------------------------------------------------------------------ #
    'btn.subscribe':        'Suscribirse',
    'btn.confirm':          'Confirmar',
    'btn.cancel':           'Cancelar',
    'btn.close':            'Cerrar',
    'btn.filter':           'Filtrar',
    'btn.reload':           'Recargar suscripciones',
    'btn.unsubscribe':      'Cancelar suscripción',
    'btn.refresh_gdc':      'Actualizar datos GDC',
    'btn.show_metadata':    'Mostrar metadatos',
    'btn.view_license':     'Ver licencia',
    'btn.accept':           'Aceptar',
    'btn.select':           'Seleccionar',
    'btn.unselect':         'Deseleccionar',
    'btn.select_all':       'Seleccionar / deseleccionar todo',
    'btn.toggle_nav':       'Alternar navegación',
    'btn.edit':             'Editar',

    # ------------------------------------------------------------------ #
    # Subscription sidebar (shared)                                        #
    # ------------------------------------------------------------------ #
    'sidebar.selected_topics':       'Temas seleccionados',
    'sidebar.save_directory':        'Directorio de guardado',
    'sidebar.save_directory_hint':   './',
    'sidebar.filters':               'Filtros',
    'sidebar.dataset':               'Conjunto de datos',
    'sidebar.datasets':              'Conjuntos de datos',
    'sidebar.media_types':           'Tipos de medios',
    'sidebar.bbox':                  'Extensión geográfica',
    'sidebar.north':                 'Norte',
    'sidebar.east':                  'Este',
    'sidebar.south':                 'Sur',
    'sidebar.west':                  'Oeste',
    'sidebar.date_range':            'Rango de fecha y hora',
    'sidebar.start_date':            'Fecha de inicio',
    'sidebar.end_date':              'Fecha de fin',
    'sidebar.start_date_hint':       'AAAA-MM-DD',
    'sidebar.start_time':            'Hora de inicio (UTC)',
    'sidebar.end_time':              'Hora de fin (UTC)',
    'sidebar.time_hint':             'HH:MM',
    'sidebar.custom_filters':        'Filtros personalizados',
    'sidebar.auth':                  'Autenticación',
    'sidebar.auth_none':             'Ninguna',
    'sidebar.auth_basic':            'HTTP básico',
    'sidebar.auth_bearer':           'Token Bearer',
    'sidebar.auth_username':         'Usuario',
    'sidebar.auth_password':         'Contraseña',
    'sidebar.auth_token':            'Token',

    # ------------------------------------------------------------------ #
    # Validation messages                                                  #
    # ------------------------------------------------------------------ #
    'validation.date_format':        'Use AAAA-MM-DD',
    'validation.time_format':        'Use HH:MM (24 horas)',
    'validation.date_time_errors':   'Corrija los errores de formato de fecha/hora antes de suscribirse.',
    'validation.fix_errors':         'Corrija los errores de validación antes de suscribirse.',
    'validation.auth_credentials_required': 'Complete todos los campos de credenciales requeridos.',

    # ------------------------------------------------------------------ #
    # Confirm subscription dialog                                          #
    # ------------------------------------------------------------------ #
    'dialog.confirm_title':  'Confirmar suscripción',
    'dialog.license_title':  'Revisar licencia',
    'dialog.license_msg':    'Este conjunto de datos tiene una licencia. Por favor, revísela antes de suscribirse.',

    # ------------------------------------------------------------------ #
    # Metadata dialog                                                      #
    # ------------------------------------------------------------------ #
    'metadata.id':            'ID: {id}',
    'metadata.title':         'Título: {title}',
    'metadata.description':   'Descripción: {description}',
    'metadata.keywords':      'Palabras clave:',
    'metadata.not_available': 'Metadatos no disponibles para: {id}',

    # ------------------------------------------------------------------ #
    # Catalogue view                                                       #
    # ------------------------------------------------------------------ #
    'catalogue.title':              'Vista del catálogo',
    'catalogue.not_loaded':         'Datos del catálogo no cargados',
    'catalogue.not_loaded_msg':     (
        'Los datos GDC aún se están obteniendo. Inténtelo de nuevo en un '
        'momento, o visite Configuración para activar una actualización manual.'
    ),
    'catalogue.search_label':       'Búsqueda de texto libre:',
    'catalogue.search_hint':        'ej. observaciones de superficie',
    'catalogue.data_policy':        'Política de datos',
    'catalogue.keywords_label':     'Palabras clave (separadas por comas)',
    'catalogue.bbox_label':         'Extensión geográfica:',
    'catalogue.bbox_spatial_rel':   'Relación espacial:',
    'catalogue.bbox_intersects':    'Intersecta',
    'catalogue.bbox_within':        'Contenido en',
    'catalogue.no_results':         'No se encontraron resultados.',
    'catalogue.page':               'Página',
    'catalogue.discrepancy':        'El contenido del registro difiere entre catálogos',

    # ------------------------------------------------------------------ #
    # Tree view                                                            #
    # ------------------------------------------------------------------ #
    'tree.title':         'Vista en árbol',
    'tree.filter_label':  'Filtrar temas',
    'tree.loading':       'Cargando\u2026',

    # ------------------------------------------------------------------ #
    # Manage Subscriptions view                                            #
    # ------------------------------------------------------------------ #
    'subscriptions.folder':        'Carpeta: {path}',
    'subscriptions.id':            'ID: {id}',
    'subscriptions.filter_default': 'Filtro: predeterminado',
    'subscriptions.filter_named':  'Filtro: {name}',
    'subscriptions.filter_custom': 'Filtro: personalizado',
    'subscriptions.edit_title':   'Editar suscripción',
    'subscriptions.credentials_note': 'Deje los campos secretos en blanco para conservar las credenciales existentes',
    'subscriptions.edit_load_error':       'No se pudieron cargar los detalles de la suscripción',
    'subscriptions.filter_parse_warning': 'No se pudo convertir el filtro en controles — se edita como JSON.',

    # ------------------------------------------------------------------ #
    # Settings view                                                        #
    # ------------------------------------------------------------------ #
    'settings.title':       'Configuración',
    'settings.gdc_section': 'Catálogos de descubrimiento globales',
    'settings.gdc_desc': (
        'Los registros se obtienen de los tres GDC al inicio y se fusionan. '
        'Los resultados se almacenan en caché en Redis durante 6 horas.'
    ),
    'settings.records':     '{name}: {count} registros',
    'settings.not_loaded':  '{name}: no cargado',

    # ------------------------------------------------------------------ #
    # Manual Subscribe view                                                #
    # ------------------------------------------------------------------ #
    'manual.title':       'Suscripción manual',
    'manual.description': 'Introduzca un tema WIS2, un directorio de guardado y un filtro opcional.',
    'manual.topic_label': 'Tema',
    'manual.topic_hint':  'cache/a/wis2/+/data/core/weather/surface-based-observations/#',
    'manual.target_label': 'Directorio de guardado',
    'manual.filter_label': 'Filtro (JSON)',
    'manual.filter_hint': (
        'Deje vacío para usar el filtro predeterminado, o pegue un objeto de filtro:\n'
        '{\n'
        '  "rules": [\n'
        '    {"id": "accept-all", "order": 1,\n'
        '     "match": {"always": true}, "action": "accept"}\n'
        '  ]\n'
        '}'
    ),

    # Validation
    'manual.val.topic_required':    'El tema es obligatorio',
    'manual.val.topic_format': (
        'Debe coincidir con (cache|origin)/a/wis2/{centre}/data/\u2026'
        ' \u2014 use + para comodines de un nivel, # solo al final'
    ),
    'manual.val.path_traversal':    'La traversal de ruta (..) no está permitida',
    'manual.val.path_absolute':     'Debe ser una ruta relativa (sin / inicial)',
    'manual.val.json_invalid':      'JSON inválido: {msg} (línea {lineno}, col {colno})',
    'manual.val.not_object':        'El filtro debe ser un objeto JSON { \u2026 }',
    'manual.val.missing_rules':     'El filtro debe tener una clave "rules"',
    'manual.val.rules_not_array':   '"rules" debe ser un array [ \u2026 ]',
    'manual.val.rule_not_object':   'Regla {i}: debe ser un objeto',
    'manual.val.rule_missing_field': 'Regla {i}: falta el campo obligatorio "{field}"',
    'manual.val.rule_wrong_type':   'Regla {i}: "{field}" debe ser de tipo {type_name}',
    'manual.val.rule_bad_action':   'Regla {i}: "action" debe ser una de: accept, reject, continue',

    # ------------------------------------------------------------------ #
    # Footer                                                               #
    # ------------------------------------------------------------------ #
    'footer.copyright': '\u00a9 2026 Organización Meteorológica Mundial',

    # ------------------------------------------------------------------ #
    # Accessibility / ARIA                                                 #
    # ------------------------------------------------------------------ #
    'aria.toggle_nav': 'Alternar navegación',
    'aria.discrepancy': 'El contenido del registro difiere entre catálogos',
}
