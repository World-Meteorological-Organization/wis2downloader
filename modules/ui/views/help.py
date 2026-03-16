from nicegui import ui

from i18n import current_lang


def render(container):
    lang = current_lang()
    with container:
        ui.element('iframe') \
            .props(f'src="/docs/{lang}/index.html"') \
            .classes('docs-frame') \
            .style('width: 100%;')
