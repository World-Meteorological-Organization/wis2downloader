"""French translations.

NOTE: Machine-generated — must be reviewed by a native French speaker,
especially WMO/meteorological terms (WIS2, BUFR, GRIB, etc.).
"""

STRINGS: dict[str, str] = {
    # ------------------------------------------------------------------ #
    # Navigation                                                           #
    # ------------------------------------------------------------------ #
    'nav.dashboard':  'Tableau de bord',
    'nav.catalogue':  'Vue du catalogue',
    'nav.tree':       'Vue arborescente',
    'nav.manual':     'Abonnement manuel',
    'nav.manage':     'Gérer les abonnements',
    'nav.settings':   'Paramètres',
    'nav.help':       'Aide',

    # ------------------------------------------------------------------ #
    # Buttons                                                              #
    # ------------------------------------------------------------------ #
    'btn.subscribe':        "S'abonner",
    'btn.confirm':          'Confirmer',
    'btn.cancel':           'Annuler',
    'btn.close':            'Fermer',
    'btn.filter':           'Filtrer',
    'btn.reload':           'Recharger les abonnements',
    'btn.unsubscribe':      'Se désabonner',
    'btn.refresh_gdc':      'Actualiser les données GDC',
    'btn.show_metadata':    'Afficher les métadonnées',
    'btn.select':           'Sélectionner',
    'btn.unselect':         'Désélectionner',
    'btn.select_all':       'Tout sélectionner / désélectionner',
    'btn.toggle_nav':       'Basculer la navigation',

    # ------------------------------------------------------------------ #
    # Subscription sidebar (shared)                                        #
    # ------------------------------------------------------------------ #
    'sidebar.selected_topics':       'Sujets sélectionnés',
    'sidebar.save_directory':        'Répertoire de sauvegarde',
    'sidebar.save_directory_hint':   './',
    'sidebar.filters':               'Filtres',
    'sidebar.dataset':               'Jeu de données',
    'sidebar.datasets':              'Jeux de données',
    'sidebar.media_types':           'Types de média',
    'sidebar.bbox':                  'Emprise géographique',
    'sidebar.north':                 'Nord',
    'sidebar.east':                  'Est',
    'sidebar.south':                 'Sud',
    'sidebar.west':                  'Ouest',
    'sidebar.date_range':            'Plage de dates et d\'heures',
    'sidebar.start_date':            'Date de début',
    'sidebar.end_date':              'Date de fin',
    'sidebar.start_date_hint':       'AAAA-MM-JJ',
    'sidebar.start_time':            'Heure de début (UTC)',
    'sidebar.end_time':              'Heure de fin (UTC)',
    'sidebar.time_hint':             'HH:MM',
    'sidebar.custom_filters':        'Filtres personnalisés',

    # ------------------------------------------------------------------ #
    # Validation messages                                                  #
    # ------------------------------------------------------------------ #
    'validation.date_format':        'Utiliser AAAA-MM-JJ',
    'validation.time_format':        'Utiliser HH:MM (24 heures)',
    'validation.date_time_errors':   'Corrigez les erreurs de format date/heure avant de vous abonner.',
    'validation.fix_errors':         'Corrigez les erreurs de validation avant de vous abonner.',

    # ------------------------------------------------------------------ #
    # Confirm subscription dialog                                          #
    # ------------------------------------------------------------------ #
    'dialog.confirm_title': "Confirmer l'abonnement",

    # ------------------------------------------------------------------ #
    # Metadata dialog                                                      #
    # ------------------------------------------------------------------ #
    'metadata.id':            'ID\u00a0: {id}',
    'metadata.title':         'Titre\u00a0: {title}',
    'metadata.description':   'Description\u00a0: {description}',
    'metadata.keywords':      'Mots-clés\u00a0:',
    'metadata.not_available': 'Métadonnées non disponibles pour\u00a0: {id}',

    # ------------------------------------------------------------------ #
    # Catalogue view                                                       #
    # ------------------------------------------------------------------ #
    'catalogue.title':              'Vue du catalogue',
    'catalogue.not_loaded':         'Données du catalogue non chargées',
    'catalogue.not_loaded_msg':     (
        'Les données GDC sont encore en cours de récupération. '
        'Réessayez dans un moment ou visitez les Paramètres pour '
        'déclencher une actualisation manuelle.'
    ),
    'catalogue.search_label':       'Recherche en texte libre\u00a0:',
    'catalogue.search_hint':        'ex. observations de surface',
    'catalogue.data_policy':        'Politique de données',
    'catalogue.keywords_label':     'Mots-clés (séparés par des virgules)',
    'catalogue.bbox_label':         'Emprise géographique\u00a0:',
    'catalogue.bbox_spatial_rel':   'Relation spatiale\u00a0:',
    'catalogue.bbox_intersects':    'Intersecte',
    'catalogue.bbox_within':        'Contenu dans',
    'catalogue.no_results':         'Aucun résultat trouvé.',
    'catalogue.page':               'Page',
    'catalogue.discrepancy':        'Le contenu diffère entre les catalogues',

    # ------------------------------------------------------------------ #
    # Tree view                                                            #
    # ------------------------------------------------------------------ #
    'tree.title':         'Vue arborescente',
    'tree.filter_label':  'Filtrer les sujets',
    'tree.loading':       'Chargement\u2026',

    # ------------------------------------------------------------------ #
    # Manage Subscriptions view                                            #
    # ------------------------------------------------------------------ #
    'subscriptions.folder':        'Dossier\u00a0: {path}',
    'subscriptions.id':            'ID\u00a0: {id}',
    'subscriptions.filter_default': 'Filtre\u00a0: par défaut',
    'subscriptions.filter_named':  'Filtre\u00a0: {name}',
    'subscriptions.filter_custom': 'Filtre\u00a0: personnalisé',

    # ------------------------------------------------------------------ #
    # Settings view                                                        #
    # ------------------------------------------------------------------ #
    'settings.title':       'Paramètres',
    'settings.gdc_section': 'Catalogues de découverte mondiaux',
    'settings.gdc_desc': (
        'Les enregistrements sont récupérés depuis les trois GDC au '
        'démarrage et fusionnés. Les résultats sont mis en cache dans '
        'Redis pendant 6 heures.'
    ),
    'settings.records':     '{name}\u00a0: {count} enregistrements',
    'settings.not_loaded':  '{name}\u00a0: non chargé',

    # ------------------------------------------------------------------ #
    # Manual Subscribe view                                                #
    # ------------------------------------------------------------------ #
    'manual.title':       'Abonnement manuel',
    'manual.description': 'Entrez un sujet WIS2, un répertoire de sauvegarde et un filtre optionnel.',
    'manual.topic_label': 'Sujet',
    'manual.topic_hint':  'cache/a/wis2/+/data/core/weather/surface-based-observations/#',
    'manual.target_label': 'Répertoire de sauvegarde',
    'manual.filter_label': 'Filtre (JSON)',
    'manual.filter_hint': (
        'Laissez vide pour utiliser le filtre par défaut, ou collez un objet filtre\u00a0:\n'
        '{\n'
        '  "rules": [\n'
        '    {"id": "accept-all", "order": 1,\n'
        '     "match": {"always": true}, "action": "accept"}\n'
        '  ]\n'
        '}'
    ),

    # Validation
    'manual.val.topic_required':    'Le sujet est obligatoire',
    'manual.val.topic_format': (
        'Doit correspondre à (cache|origin)/a/wis2/{centre}/data/\u2026'
        ' \u2014 utilisez + pour les jokers à un niveau, # uniquement à la fin'
    ),
    'manual.val.path_traversal':    'La traversée de chemin (..) n\'est pas autorisée',
    'manual.val.path_absolute':     'Doit être un chemin relatif (sans / initial)',
    'manual.val.json_invalid':      'JSON invalide\u00a0: {msg} (ligne {lineno}, col {colno})',
    'manual.val.not_object':        'Le filtre doit être un objet JSON { \u2026 }',
    'manual.val.missing_rules':     'Le filtre doit avoir une clé "rules"',
    'manual.val.rules_not_array':   '"rules" doit être un tableau [ \u2026 ]',
    'manual.val.rule_not_object':   'Règle {i}\u00a0: doit être un objet',
    'manual.val.rule_missing_field': 'Règle {i}\u00a0: champ obligatoire manquant "{field}"',
    'manual.val.rule_wrong_type':   'Règle {i}\u00a0: "{field}" doit être de type {type_name}',
    'manual.val.rule_bad_action':   'Règle {i}\u00a0: "action" doit être l\'une de\u00a0: accept, reject, continue',

    # ------------------------------------------------------------------ #
    # Footer                                                               #
    # ------------------------------------------------------------------ #
    'footer.copyright': '\u00a9 2026 Organisation météorologique mondiale',

    # ------------------------------------------------------------------ #
    # Accessibility / ARIA                                                 #
    # ------------------------------------------------------------------ #
    'aria.toggle_nav': 'Basculer la navigation',
    'aria.discrepancy': 'Le contenu diffère entre les catalogues',
}
