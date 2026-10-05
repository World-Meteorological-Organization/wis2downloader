"""Per-browser UI preferences (lang, view, nav_mini).

With cookie consent they are kept in cookies: read from the page request, written by the browser.
Without consent nothing is stored, not even the refusal: a language change carries the preferences
in the reload URL, for that visit only. Values come from the client, so callers must check them.
"""
import json
from urllib.parse import urlencode

from nicegui import app, context, ui

_MAX_AGE = 365 * 24 * 3600  # one year


def _write_cookie(name: str, value: str) -> None:
    ui.run_javascript(
        f"document.cookie = 'wis2_{name}=' + encodeURIComponent({json.dumps(value)}) "
        f"+ '; path=/; max-age={_MAX_AGE}; SameSite=Strict';")


def get_pref(name: str) -> str | None:
    """Preference *name* from the page request: cookies if it was loaded with consent, else the URL."""
    request = context.client.request
    if request is None:
        return None
    if request.cookies.get('wis2_consent') == '1':
        return request.cookies.get(f'wis2_{name}')
    return request.query_params.get(name)


def has_consent() -> bool:
    """True if cookies may be stored: consent cookie sent with the page, or accepted since."""
    if 'consent' not in app.storage.client:
        request = context.client.request
        app.storage.client['consent'] = request is not None and request.cookies.get('wis2_consent') == '1'
    return app.storage.client['consent']


def declined() -> bool:
    """True if cookies were declined during this visit (kept in memory and the URL only)."""
    request = context.client.request
    from_url = request is not None and request.query_params.get('cookies') == 'declined'
    return app.storage.client.get('declined', False) or from_url


def accept(prefs: dict[str, str]) -> None:
    """Record consent and store the current preferences."""
    app.storage.client['consent'] = True
    _write_cookie('consent', '1')
    for name, value in prefs.items():
        set_pref(name, value)


def decline() -> None:
    app.storage.client['declined'] = True


def set_pref(name: str, value: str) -> None:
    """Store preference *name* in the browser if cookies are accepted; otherwise do nothing."""
    if has_consent():
        _write_cookie(name, value)


def prefs_url(prefs: dict[str, str]) -> str:
    """Page URL carrying *prefs* (and a refusal made in this visit) when cookies are not accepted."""
    params = dict(prefs, **({'cookies': 'declined'} if declined() else {}))
    return '/?' + urlencode(params)
