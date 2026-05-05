"""Chinese (Simplified) translations.

NOTE: Machine-generated — must be reviewed by a native Chinese speaker,
especially WMO/meteorological terms (WIS2, BUFR, GRIB, etc.).
"""

STRINGS: dict[str, str] = {
    # ------------------------------------------------------------------ #
    # Navigation                                                           #
    # ------------------------------------------------------------------ #
    'nav.dashboard':  '仪表板',
    'nav.catalogue':  '目录视图',
    'nav.tree':       '树形视图',
    'nav.manual':     '手动订阅',
    'nav.manage':     '管理订阅',
    'nav.settings':   '设置',
    'nav.help':       '帮助',

    # ------------------------------------------------------------------ #
    # Buttons                                                              #
    # ------------------------------------------------------------------ #
    'btn.subscribe':        '订阅',
    'btn.confirm':          '确认',
    'btn.cancel':           '取消',
    'btn.close':            '关闭',
    'btn.filter':           '筛选',
    'btn.reload':           '重新加载订阅',
    'btn.unsubscribe':      '取消订阅',
    'btn.refresh_gdc':      '刷新 GDC 数据',
    'btn.show_metadata':    '显示元数据',
    'btn.view_license':     '查看许可证',
    'btn.select':           '选择',
    'btn.unselect':         '取消选择',
    'btn.select_all':       '全选 / 全不选',
    'btn.toggle_nav':       '切换导航',

    # ------------------------------------------------------------------ #
    # Subscription sidebar (shared)                                        #
    # ------------------------------------------------------------------ #
    'sidebar.selected_topics':       '已选主题',
    'sidebar.save_directory':        '保存目录',
    'sidebar.save_directory_hint':   './',
    'sidebar.filters':               '过滤器',
    'sidebar.dataset':               '数据集',
    'sidebar.datasets':              '数据集',
    'sidebar.media_types':           '媒体类型',
    'sidebar.bbox':                  '地理范围',
    'sidebar.north':                 '北',
    'sidebar.east':                  '东',
    'sidebar.south':                 '南',
    'sidebar.west':                  '西',
    'sidebar.date_range':            '日期和时间范围',
    'sidebar.start_date':            '开始日期',
    'sidebar.end_date':              '结束日期',
    'sidebar.start_date_hint':       'YYYY-MM-DD',
    'sidebar.start_time':            '开始时间（UTC）',
    'sidebar.end_time':              '结束时间（UTC）',
    'sidebar.time_hint':             'HH:MM',
    'sidebar.custom_filters':        '自定义过滤器',

    # ------------------------------------------------------------------ #
    # Validation messages                                                  #
    # ------------------------------------------------------------------ #
    'validation.date_format':        '请使用 YYYY-MM-DD 格式',
    'validation.time_format':        '请使用 HH:MM（24小时制）格式',
    'validation.date_time_errors':   '请在订阅前修正日期/时间格式错误。',
    'validation.fix_errors':         '请在订阅前修正验证错误。',

    # ------------------------------------------------------------------ #
    # Confirm subscription dialog                                          #
    # ------------------------------------------------------------------ #
    'dialog.confirm_title': '确认订阅',

    # ------------------------------------------------------------------ #
    # Metadata dialog                                                      #
    # ------------------------------------------------------------------ #
    'metadata.id':            'ID：{id}',
    'metadata.title':         '标题：{title}',
    'metadata.description':   '描述：{description}',
    'metadata.keywords':      '关键词：',
    'metadata.not_available': '{id} 的元数据不可用',

    # ------------------------------------------------------------------ #
    # Catalogue view                                                       #
    # ------------------------------------------------------------------ #
    'catalogue.title':              '目录视图',
    'catalogue.not_loaded':         '目录数据未加载',
    'catalogue.not_loaded_msg':     (
        'GDC 数据仍在获取中，请稍后重试，'
        '或前往设置页面手动触发刷新。'
    ),
    'catalogue.search_label':       '全文搜索：',
    'catalogue.search_hint':        '例如：地面观测',
    'catalogue.data_policy':        '数据政策',
    'catalogue.keywords_label':     '关键词（逗号分隔）',
    'catalogue.bbox_label':         '地理范围：',
    'catalogue.bbox_spatial_rel':   '空间关系：',
    'catalogue.bbox_intersects':    '相交',
    'catalogue.bbox_within':        '包含于',
    'catalogue.no_results':         '未找到结果。',
    'catalogue.page':               '页',
    'catalogue.discrepancy':        '记录内容在各目录间存在差异',

    # ------------------------------------------------------------------ #
    # Tree view                                                            #
    # ------------------------------------------------------------------ #
    'tree.title':         '树形视图',
    'tree.filter_label':  '筛选主题',
    'tree.loading':       '加载中\u2026',

    # ------------------------------------------------------------------ #
    # Manage Subscriptions view                                            #
    # ------------------------------------------------------------------ #
    'subscriptions.folder':        '文件夹：{path}',
    'subscriptions.id':            'ID：{id}',
    'subscriptions.filter_default': '过滤器：默认',
    'subscriptions.filter_named':  '过滤器：{name}',
    'subscriptions.filter_custom': '过滤器：自定义',

    # ------------------------------------------------------------------ #
    # Settings view                                                        #
    # ------------------------------------------------------------------ #
    'settings.title':       '设置',
    'settings.gdc_section': '全球发现目录',
    'settings.gdc_desc': (
        '启动时从所有三个 GDC 获取记录并合并。'
        '结果在 Redis 中缓存 6 小时。'
    ),
    'settings.records':     '{name}：{count} 条记录',
    'settings.not_loaded':  '{name}：未加载',

    # ------------------------------------------------------------------ #
    # Manual Subscribe view                                                #
    # ------------------------------------------------------------------ #
    'manual.title':       '手动订阅',
    'manual.description': '请输入 WIS2 主题、保存目录和可选的过滤器。',
    'manual.topic_label': '主题',
    'manual.topic_hint':  'cache/a/wis2/+/data/core/weather/surface-based-observations/#',
    'manual.target_label': '保存目录',
    'manual.filter_label': '过滤器（JSON）',
    'manual.filter_hint': (
        '留空以使用默认过滤器，或粘贴过滤器对象：\n'
        '{\n'
        '  "rules": [\n'
        '    {"id": "accept-all", "order": 1,\n'
        '     "match": {"always": true}, "action": "accept"}\n'
        '  ]\n'
        '}'
    ),

    # Validation
    'manual.val.topic_required':    '主题为必填项',
    'manual.val.topic_format': (
        '必须匹配 (cache|origin)/a/wis2/{centre}/data/\u2026'
        ' \u2014 用 + 表示单级通配符，# 只能在末尾使用'
    ),
    'manual.val.path_traversal':    '不允许路径遍历（..）',
    'manual.val.path_absolute':     '必须是相对路径（不能以 / 开头）',
    'manual.val.json_invalid':      'JSON 无效：{msg}（第 {lineno} 行，第 {colno} 列）',
    'manual.val.not_object':        '过滤器必须是 JSON 对象 { \u2026 }',
    'manual.val.missing_rules':     '过滤器必须包含 "rules" 键',
    'manual.val.rules_not_array':   '"rules" 必须是数组 [ \u2026 ]',
    'manual.val.rule_not_object':   '规则 {i}：必须是对象',
    'manual.val.rule_missing_field': '规则 {i}：缺少必填字段 "{field}"',
    'manual.val.rule_wrong_type':   '规则 {i}："{field}" 必须是 {type_name} 类型',
    'manual.val.rule_bad_action':   '规则 {i}："action" 必须是以下之一：accept, reject, continue',

    # ------------------------------------------------------------------ #
    # Footer                                                               #
    # ------------------------------------------------------------------ #
    'footer.copyright': '\u00a9 2026 世界气象组织',

    # ------------------------------------------------------------------ #
    # Accessibility / ARIA                                                 #
    # ------------------------------------------------------------------ #
    'aria.toggle_nav': '切换导航',
    'aria.discrepancy': '记录内容在各目录间存在差异',
}
