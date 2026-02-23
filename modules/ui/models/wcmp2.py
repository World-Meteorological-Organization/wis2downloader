"""WCMP2 (WMO Core Metadata Profile 2) data model.

Typed dataclasses for discovery-metadata records as returned by a GDC
(Global Discovery Catalogue) collection endpoint.

Schema reference:
  https://github.com/wmo-im/wcmp2/blob/main/schemas/wcmp2-bundled.json
"""

from dataclasses import dataclass, field
from typing import Any, Literal, Self


# ---------------------------------------------------------------------------
# Leaf types
# ---------------------------------------------------------------------------

@dataclass
class Concept:
    """A single term within a controlled vocabulary theme."""
    id: str
    title: str | None = None
    description: str | None = None
    url: str | None = None

    @classmethod
    def from_dict(cls, d: dict) -> Self:
        return cls(
            id=d['id'],
            title=d.get('title'),
            description=d.get('description'),
            url=d.get('url'),
        )


@dataclass
class Theme:
    """A vocabulary scheme and the concepts selected from it."""
    concepts: list[Concept]
    scheme: str

    @classmethod
    def from_dict(cls, d: dict) -> Self:
        return cls(
            concepts=[Concept.from_dict(c) for c in d.get('concepts', [])],
            scheme=d.get('scheme', ''),
        )


@dataclass
class Link:
    """A hyperlink as defined in OGC API / WCMP2.

    The ``channel`` field carries the MQTT topic used for broker-based
    data access (i.e. WIS2 cache topics such as ``cache/a/wis2/…``).

    ``extra`` captures any non-schema keys present in the raw dict (e.g.
    custom GDC extensions such as ``filters``).
    """
    href: str
    rel: str | None = None
    type: str | None = None
    hreflang: str | None = None
    title: str | None = None
    length: int | None = None
    channel: str | None = None
    security: dict | None = None
    distribution: dict | None = None
    extra: dict = field(default_factory=dict)

    _KNOWN_KEYS = frozenset({
        'href', 'rel', 'type', 'hreflang', 'title',
        'length', 'channel', 'security', 'distribution',
    })

    @classmethod
    def from_dict(cls, d: dict) -> Self:
        return cls(
            href=d['href'],
            rel=d.get('rel'),
            type=d.get('type'),
            hreflang=d.get('hreflang'),
            title=d.get('title'),
            length=d.get('length'),
            channel=d.get('channel'),
            security=d.get('security'),
            distribution=d.get('distribution'),
            extra={k: v for k, v in d.items() if k not in cls._KNOWN_KEYS},
        )


@dataclass
class Contact:
    """A responsible party for the dataset."""
    organization: str
    name: str | None = None
    identifier: str | None = None
    position: str | None = None
    phones: list[dict] | None = None
    emails: list[dict] | None = None
    addresses: list[dict] | None = None
    links: list[Link] | None = None
    hours_of_service: str | None = None
    contact_instructions: str | None = None
    roles: list[str] | None = None
    logo: Link | None = None

    @classmethod
    def from_dict(cls, d: dict) -> Self:
        return cls(
            organization=d.get('organization', ''),
            name=d.get('name'),
            identifier=d.get('identifier'),
            position=d.get('position'),
            phones=d.get('phones'),
            emails=d.get('emails'),
            addresses=d.get('addresses'),
            links=[Link.from_dict(lnk) for lnk in d['links']] if 'links' in d else None,
            hours_of_service=d.get('hoursOfService'),
            contact_instructions=d.get('contactInstructions'),
            roles=d.get('roles'),
            logo=Link.from_dict(d['logo']) if 'logo' in d else None,
        )


# ---------------------------------------------------------------------------
# Geometry and time
# ---------------------------------------------------------------------------

@dataclass
class Geometry:
    """GeoJSON geometry.

    ``coordinates`` structure varies by ``type``; ``geometries`` is only
    populated for GeometryCollection.
    """
    type: str
    coordinates: Any | None = None
    geometries: list[dict] | None = None

    @classmethod
    def from_dict(cls, d: dict) -> Self:
        return cls(
            type=d['type'],
            coordinates=d.get('coordinates'),
            geometries=d.get('geometries'),
        )


@dataclass
class Time:
    """Temporal extent of the dataset.

    Exactly one of ``date``, ``timestamp``, or ``interval`` will be set.
    ``resolution`` is optional and uses ISO 8601 duration notation (e.g. "P1D").
    Open-ended intervals use ".." as per ISO 8601.
    """
    date: str | None = None
    timestamp: str | None = None
    interval: list[str] | None = None
    resolution: str | None = None

    @classmethod
    def from_dict(cls, d: dict) -> Self:
        return cls(
            date=d.get('date'),
            timestamp=d.get('timestamp'),
            interval=d.get('interval'),
            resolution=d.get('resolution'),
        )


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------

@dataclass
class Properties:
    """The ``properties`` object of a WCMP2 Feature record."""
    type: str
    title: str
    description: str
    contacts: list[Contact]
    created: str                                              # ISO 8601 datetime
    keywords: list[str] | None = None
    themes: list[Theme] | None = None
    version: str | None = None
    external_ids: list[dict] | None = None
    updated: str | None = None                               # ISO 8601 datetime
    # Schema key is "wmo:dataPolicy" — colon is invalid in Python identifiers
    wmo_data_policy: Literal['core', 'recommended'] | None = None
    rights: str | None = None

    @classmethod
    def from_dict(cls, d: dict) -> Self:
        return cls(
            type=d.get('type', ''),
            title=d.get('title', ''),
            description=d.get('description', ''),
            contacts=[Contact.from_dict(c) for c in d.get('contacts', [])],
            created=d.get('created', ''),
            keywords=d.get('keywords'),
            themes=[Theme.from_dict(t) for t in d['themes']] if 'themes' in d else None,
            version=d.get('version'),
            external_ids=d.get('externalIds'),
            updated=d.get('updated'),
            wmo_data_policy=d.get('wmo:dataPolicy'),
            rights=d.get('rights'),
        )


# ---------------------------------------------------------------------------
# Top-level record
# ---------------------------------------------------------------------------

@dataclass
class WCMP2Record:
    """A WCMP2 discovery metadata record (GeoJSON Feature).

    Conforms to: http://wis.wmo.int/spec/wcmp/2/conf/core

    Parse from a raw GDC API dict with ``WCMP2Record.from_dict(d)``.
    """
    id: str
    conforms_to: list[str]
    type: str                                   # always "Feature"
    properties: Properties
    links: list[Link]
    geometry: Geometry | None = None            # null is valid per schema
    time: Time | None = None                    # null is valid per schema
    additional_extents: dict | None = None
    link_templates: list[dict] | None = None

    @classmethod
    def from_dict(cls, d: dict) -> Self:
        geometry_raw = d.get('geometry')
        time_raw = d.get('time')
        return cls(
            id=str(d['id']),
            conforms_to=d.get('conformsTo', []),
            type=d.get('type', 'Feature'),
            properties=Properties.from_dict(d.get('properties', {})),
            links=[Link.from_dict(lnk) for lnk in d.get('links', [])],
            geometry=Geometry.from_dict(geometry_raw) if geometry_raw else None,
            time=Time.from_dict(time_raw) if isinstance(time_raw, dict) else None,
            additional_extents=d.get('additionalExtents'),
            link_templates=d.get('linkTemplates'),
        )

    # --- Convenience accessors (mirror the most-used dict paths) -----------

    @property
    def title(self) -> str:
        return self.properties.title

    @property
    def description(self) -> str:
        return self.properties.description

    @property
    def wmo_data_policy(self) -> Literal['core', 'recommended'] | None:
        return self.properties.wmo_data_policy

    @property
    def keywords(self) -> list[str]:
        return self.properties.keywords or []

    @property
    def mqtt_channels(self) -> list[str]:
        """MQTT topic channels from all links (i.e. WIS2 cache topics)."""
        return [lnk.channel for lnk in self.links if lnk.channel]
