"""Arabic translations (RTL).

NOTE: Machine-generated — must be reviewed by a native Arabic speaker,
especially WMO/meteorological terms (WIS2, BUFR, GRIB, etc.).
"""

STRINGS: dict[str, str] = {
    # ------------------------------------------------------------------ #
    # Navigation                                                           #
    # ------------------------------------------------------------------ #
    'nav.dashboard':  'لوحة التحكم',
    'nav.catalogue':  'عرض الكتالوج',
    'nav.tree':       'العرض الشجري',
    'nav.manual':     'اشتراك يدوي',
    'nav.manage':     'إدارة الاشتراكات',
    'nav.settings':   'الإعدادات',
    'nav.help':       'مساعدة',

    # ------------------------------------------------------------------ #
    # Buttons                                                              #
    # ------------------------------------------------------------------ #
    'btn.subscribe':        'اشتراك',
    'btn.confirm':          'تأكيد',
    'btn.cancel':           'إلغاء',
    'btn.close':            'إغلاق',
    'btn.filter':           'تصفية',
    'btn.reload':           'إعادة تحميل الاشتراكات',
    'btn.unsubscribe':      'إلغاء الاشتراك',
    'btn.refresh_gdc':      'تحديث بيانات GDC',
    'btn.show_metadata':    'عرض البيانات الوصفية',
    'btn.view_license':     'عرض الترخيص',
    'btn.accept':           'قبول',
    'btn.select':           'تحديد',
    'btn.unselect':         'إلغاء التحديد',
    'btn.select_all':       'تحديد / إلغاء تحديد الكل',
    'btn.toggle_nav':       'تبديل التنقل',

    # ------------------------------------------------------------------ #
    # Subscription sidebar (shared)                                        #
    # ------------------------------------------------------------------ #
    'sidebar.selected_topics':       'المواضيع المحددة',
    'sidebar.save_directory':        'مجلد الحفظ',
    'sidebar.save_directory_hint':   './',
    'sidebar.filters':               'المرشحات',
    'sidebar.dataset':               'مجموعة البيانات',
    'sidebar.datasets':              'مجموعات البيانات',
    'sidebar.media_types':           'أنواع الوسائط',
    'sidebar.bbox':                  'نطاق جغرافي',
    'sidebar.north':                 'شمال',
    'sidebar.east':                  'شرق',
    'sidebar.south':                 'جنوب',
    'sidebar.west':                  'غرب',
    'sidebar.date_range':            'نطاق التاريخ والوقت',
    'sidebar.start_date':            'تاريخ البدء',
    'sidebar.end_date':              'تاريخ الانتهاء',
    'sidebar.start_date_hint':       'YYYY-MM-DD',
    'sidebar.start_time':            'وقت البدء (UTC)',
    'sidebar.end_time':              'وقت الانتهاء (UTC)',
    'sidebar.time_hint':             'HH:MM',
    'sidebar.custom_filters':        'مرشحات مخصصة',
    'sidebar.auth':                  'المصادقة',
    'sidebar.auth_none':             'بدون',
    'sidebar.auth_basic':            'مصادقة أساسية',
    'sidebar.auth_bearer':           'رمز الحامل',
    'sidebar.auth_username':         'اسم المستخدم',
    'sidebar.auth_password':         'كلمة المرور',
    'sidebar.auth_token':            'الرمز',

    # ------------------------------------------------------------------ #
    # Validation messages                                                  #
    # ------------------------------------------------------------------ #
    'validation.date_format':        'استخدم YYYY-MM-DD',
    'validation.time_format':        'استخدم HH:MM (24 ساعة)',
    'validation.date_time_errors':   'يرجى تصحيح أخطاء تنسيق التاريخ/الوقت قبل الاشتراك.',
    'validation.fix_errors':         'يرجى تصحيح أخطاء التحقق قبل الاشتراك.',
    'validation.auth_credentials_required': 'يرجى ملء جميع حقول بيانات الاعتماد المطلوبة.',

    # ------------------------------------------------------------------ #
    # Confirm subscription dialog                                          #
    # ------------------------------------------------------------------ #
    'dialog.confirm_title':  'تأكيد الاشتراك',
    'dialog.license_title':  'مراجعة الترخيص',
    'dialog.license_msg':    'يحتوي هذا المجموعة على ترخيص. يرجى مراجعته قبل الاشتراك.',

    # ------------------------------------------------------------------ #
    # Metadata dialog                                                      #
    # ------------------------------------------------------------------ #
    'metadata.id':            'المعرف: {id}',
    'metadata.title':         'العنوان: {title}',
    'metadata.description':   'الوصف: {description}',
    'metadata.keywords':      'الكلمات المفتاحية:',
    'metadata.not_available': 'البيانات الوصفية غير متاحة لـ: {id}',

    # ------------------------------------------------------------------ #
    # Catalogue view                                                       #
    # ------------------------------------------------------------------ #
    'catalogue.title':              'عرض الكتالوج',
    'catalogue.not_loaded':         'لم يتم تحميل بيانات الكتالوج',
    'catalogue.not_loaded_msg':     (
        'لا تزال بيانات GDC قيد الجلب. حاول مرة أخرى بعد لحظة، '
        'أو قم بزيارة الإعدادات لبدء تحديث يدوي.'
    ),
    'catalogue.search_label':       'بحث نصي حر:',
    'catalogue.search_hint':        'مثال: ملاحظات السطح',
    'catalogue.data_policy':        'سياسة البيانات',
    'catalogue.keywords_label':     'الكلمات المفتاحية (مفصولة بفواصل)',
    'catalogue.bbox_label':         'النطاق الجغرافي:',
    'catalogue.bbox_spatial_rel':   'العلاقة المكانية:',
    'catalogue.bbox_intersects':    'يتقاطع مع',
    'catalogue.bbox_within':        'ضمن',
    'catalogue.no_results':         'لم يتم العثور على نتائج.',
    'catalogue.page':               'صفحة',
    'catalogue.discrepancy':        'يختلف محتوى السجل بين الكتالوجات',

    # ------------------------------------------------------------------ #
    # Tree view                                                            #
    # ------------------------------------------------------------------ #
    'tree.title':         'العرض الشجري',
    'tree.filter_label':  'تصفية المواضيع',
    'tree.loading':       'جارٍ التحميل\u2026',

    # ------------------------------------------------------------------ #
    # Manage Subscriptions view                                            #
    # ------------------------------------------------------------------ #
    'subscriptions.folder':        'المجلد: {path}',
    'subscriptions.id':            'المعرف: {id}',
    'subscriptions.filter_default': 'الفلتر: افتراضي',
    'subscriptions.filter_named':  'الفلتر: {name}',
    'subscriptions.filter_custom': 'الفلتر: مخصص',

    # ------------------------------------------------------------------ #
    # Settings view                                                        #
    # ------------------------------------------------------------------ #
    'settings.title':       'الإعدادات',
    'settings.gdc_section': 'كتالوجات الاكتشاف العالمية',
    'settings.gdc_desc': (
        'يتم جلب السجلات من الكتالوجات الثلاثة GDC عند بدء التشغيل ودمجها. '
        'يتم تخزين النتائج مؤقتًا في Redis لمدة 6 ساعات.'
    ),
    'settings.records':     '{name}: {count} سجل',
    'settings.not_loaded':  '{name}: غير محمّل',

    # ------------------------------------------------------------------ #
    # Manual Subscribe view                                                #
    # ------------------------------------------------------------------ #
    'manual.title':       'اشتراك يدوي',
    'manual.description': 'أدخل موضوع WIS2 ومجلد الحفظ ومرشحًا اختياريًا.',
    'manual.topic_label': 'الموضوع',
    'manual.topic_hint':  'cache/a/wis2/+/data/core/weather/surface-based-observations/#',
    'manual.target_label': 'مجلد الحفظ',
    'manual.filter_label': 'المرشح (JSON)',
    'manual.filter_hint': (
        'اتركه فارغًا لاستخدام المرشح الافتراضي، أو الصق كائن مرشح:\n'
        '{\n'
        '  "rules": [\n'
        '    {"id": "accept-all", "order": 1,\n'
        '     "match": {"always": true}, "action": "accept"}\n'
        '  ]\n'
        '}'
    ),

    # Validation
    'manual.val.topic_required':    'الموضوع مطلوب',
    'manual.val.topic_format': (
        'يجب أن يطابق (cache|origin)/a/wis2/{centre}/data/\u2026'
        ' \u2014 استخدم + لبدائل المستوى الواحد، و # في النهاية فقط'
    ),
    'manual.val.path_traversal':    'اجتياز المسار (..) غير مسموح به',
    'manual.val.path_absolute':     'يجب أن يكون مسارًا نسبيًا (بدون / في البداية)',
    'manual.val.json_invalid':      'JSON غير صالح: {msg} (سطر {lineno}، عمود {colno})',
    'manual.val.not_object':        'يجب أن يكون المرشح كائن JSON { \u2026 }',
    'manual.val.missing_rules':     'يجب أن يحتوي المرشح على مفتاح "rules"',
    'manual.val.rules_not_array':   'يجب أن تكون "rules" مصفوفة [ \u2026 ]',
    'manual.val.rule_not_object':   'القاعدة {i}: يجب أن تكون كائنًا',
    'manual.val.rule_missing_field': 'القاعدة {i}: الحقل المطلوب "{field}" مفقود',
    'manual.val.rule_wrong_type':   'القاعدة {i}: يجب أن يكون "{field}" من نوع {type_name}',
    'manual.val.rule_bad_action':   'القاعدة {i}: يجب أن تكون "action" إحدى: accept, reject, continue',

    # ------------------------------------------------------------------ #
    # Footer                                                               #
    # ------------------------------------------------------------------ #
    'footer.copyright': '\u00a9 2026 المنظمة العالمية للأرصاد الجوية',

    # ------------------------------------------------------------------ #
    # Accessibility / ARIA                                                 #
    # ------------------------------------------------------------------ #
    'aria.toggle_nav': 'تبديل التنقل',
    'aria.discrepancy': 'يختلف محتوى السجل بين الكتالوجات',
}
