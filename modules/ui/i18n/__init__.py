"""Internationalisation helpers for the WIS2 Downloader UI.

Usage::

    from i18n import t, LANGUAGES, current_lang, is_rtl

    ui.label(t('nav.dashboard'))
    ui.input(label=t('sidebar.save_directory'))
    t('subscriptions.folder', path='/data/synop')

The current language comes from the browser's ``lang`` preference cookie
(see ``prefs``) and defaults to English.  Call ``t()`` during render time
(inside a ``@ui.page`` handler or a NiceGUI event callback) so that the
page request is available.

All translations fall back to English if a key is missing in the chosen
language file.  If the key is missing in English too, the key string itself
is returned so that missing translations are immediately visible during
development.

NOTE: Machine-generated translations are provided as a starting point.
      All non-English strings should be reviewed by a native speaker,
      especially WMO/meteorological domain terms (WIS2, BUFR, GRIB, etc.)
      which have established translations in WMO official documents.
"""

from prefs import get_pref

from . import ar, en, es, fr, ru, zh

# Maps language code → display name (in the native script)
LANGUAGES: dict[str, str] = {
    'en': 'English',
    'fr': 'Français',
    'es': 'Español',
    'ar': 'العربية',
    'zh': '中文',
    'ru': 'Русский',
}

RTL_LANGUAGES: frozenset[str] = frozenset({'ar'})

_STRINGS: dict[str, dict[str, str]] = {
    'en': en.STRINGS,
    'fr': fr.STRINGS,
    'es': es.STRINGS,
    'ar': ar.STRINGS,
    'zh': zh.STRINGS,
    'ru': ru.STRINGS,
}


def current_lang() -> str:
    """Return the active language code: the ``lang`` cookie if it is a known language, else English."""
    lang = get_pref('lang')
    return lang if lang in LANGUAGES else 'en'


def is_rtl() -> bool:
    """True when the current language is written right-to-left."""
    return current_lang() in RTL_LANGUAGES


def t(key: str, **kwargs) -> str:
    """Look up *key* in the current language, falling back to English.

    Keyword arguments are interpolated via ``str.format``, e.g.::

        t('subscriptions.folder', path='/data/synop')
    """
    lang = current_lang()
    strings = _STRINGS.get(lang, en.STRINGS)
    template = strings.get(key) or en.STRINGS.get(key) or key
    return template.format(**kwargs) if kwargs else template
