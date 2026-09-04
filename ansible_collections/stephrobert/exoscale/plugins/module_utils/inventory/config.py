# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Stéphane Robert
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Ce que l'utilisateur a demandé, lu une fois et validé une fois.

Le plugin lit ses options par `self.get_option` ; cette couche les transforme
en objets typés que les autres couches savent consommer. Elle ne connaît ni
Ansible ni le SDK, donc elle se teste avec un simple dictionnaire.

Elle porte aussi la clé de cache : tout ce qui change le résultat entre dans
la clé, la clé d'API comprise, par son empreinte. Deux exécutions sur deux
comptes sans profil déclaré partageraient sinon le même parc en cache.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from .address import DEFAULT_PRIORITY, FAMILIES, AddressPolicy
from .filtering import Filters
from .groups import AXES
from .hostname import is_known_source

#: Les axes de groupes proposés par défaut. Assez pour reconnaître son parc,
#: pas assez pour produire des centaines de groupes vides.
DEFAULT_GROUP_BY: tuple[str, ...] = ("product", "zone", "state")

#: Les sources de nom d'hôte par défaut. Le nom d'abord, l'identifiant en
#: dernier recours : un nom d'hôte qui est une adresse change dès que
#: l'adresse change.
DEFAULT_HOSTNAMES: tuple[str, ...] = ("name", "id")


class ConfigError(ValueError):
    """La configuration demande quelque chose que le plugin ne sait pas faire."""


@dataclass(frozen=True)
class InventoryConfig:
    """La configuration entière, sous une forme que les couches consomment."""

    products: tuple[str, ...]
    zones: tuple[str, ...]
    hostnames: tuple[str, ...]
    address: AddressPolicy
    require_address: bool
    group_by: tuple[str, ...]
    filters: Filters
    include_raw: bool
    strict: bool

    def cache_fingerprint(self, api_url: str | None, api_key: str | None = None) -> str:
        """Une empreinte de tout ce qui change le résultat.

        Seule l'empreinte de la clé entre ici, jamais sa valeur. `strict` en
        fait partie : il décide si une découverte partielle échoue ou passe,
        donc il change le résultat.
        """
        materiel = {
            "api_url": api_url,
            "identity": hashlib.sha256((api_key or "").encode("utf-8")).hexdigest()[:16],
            "products": self.products,
            "zones": self.zones,
            "hostnames": self.hostnames,
            "address": [self.address.priority, self.address.private_network],
            "group_by": self.group_by,
            "filters": [
                dict(self.filters.labels),
                self.filters.labels_match,
                self.filters.states,
                dict(self.filters.exclude_labels),
                self.filters.exclude_states,
            ],
            "include_raw": self.include_raw,
            "strict": self.strict,
        }
        serialise = json.dumps(materiel, sort_keys=True, default=list)
        return hashlib.sha256(serialise.encode("utf-8")).hexdigest()[:16]


def _liste(valeur: Any) -> tuple[str, ...]:
    if valeur is None:
        return ()
    if isinstance(valeur, str):
        return (valeur,)
    return tuple(str(item) for item in valeur)


def _labels(valeur: Any) -> dict[str, str]:
    """Un dictionnaire de labels, une valeur vide voulant dire « la clé existe »."""
    if not valeur:
        return {}
    if not isinstance(valeur, Mapping):
        raise ConfigError(f"un filtre de labels est un dictionnaire, pas {type(valeur).__name__}")
    return {str(cle): "" if item is None else str(item) for cle, item in valeur.items()}


def from_options(
    get_option: Callable[[str], Any],
    known_products: tuple[str, ...],
    known_zones: tuple[str, ...] = (),
) -> InventoryConfig:
    """Lit et valide les options, et refuse ce qu'elle ne sait pas faire.

    Un nom inconnu dans `products`, `group_by`, `zones` ou `address_priority`
    est une faute de configuration. L'ignorer produirait un inventaire
    silencieusement différent de ce qui a été demandé.
    """
    produits = _liste(get_option("products")) or ("all",)
    if produits == ("all",):
        produits = known_products
    inconnus = sorted(set(produits) - set(known_products))
    if inconnus:
        raise ConfigError(f"produit(s) inconnu(s) : {inconnus}. Connus : {list(known_products)}")

    axes = _liste(get_option("group_by")) or DEFAULT_GROUP_BY
    hors_axes = sorted(set(axes) - set(AXES))
    if hors_axes:
        raise ConfigError(f"axe(s) de groupe inconnu(s) : {hors_axes}. Connus : {list(AXES)}")

    priorite = _liste(get_option("address_priority")) or DEFAULT_PRIORITY
    hors_familles = sorted(set(priorite) - set(FAMILIES))
    if hors_familles:
        raise ConfigError(
            f"famille(s) d'adresse inconnue(s) : {hors_familles}. Connues : {list(FAMILIES)}"
        )

    zones = _liste(get_option("zones"))
    if known_zones:
        hors_zones = sorted(set(zones) - set(known_zones))
        if hors_zones:
            raise ConfigError(f"zone(s) inconnue(s) : {hors_zones}. Connues : {list(known_zones)}")

    sources = _liste(get_option("hostnames")) or DEFAULT_HOSTNAMES
    hors_sources = sorted(nom for nom in sources if not is_known_source(nom))
    if hors_sources:
        raise ConfigError(
            f"source(s) de nom d'hôte inconnue(s) : {hors_sources}. "
            f"Connues : {list(DEFAULT_HOSTNAMES)}, les familles d'adresses, et `label:<clé>`"
        )

    correspondance = get_option("labels_match") or "any"
    if correspondance not in ("any", "all"):
        raise ConfigError(f"labels_match vaut '{correspondance}', attendu 'any' ou 'all'")

    adresse = get_option("address") or {}
    exclusions = get_option("exclude") or {}
    return InventoryConfig(
        products=tuple(produits),
        zones=zones,
        hostnames=sources,
        address=AddressPolicy(
            priority=tuple(priorite),
            private_network=adresse.get("private_network") or adresse.get("private_network_id"),
        ),
        require_address=bool(get_option("require_address")),
        group_by=tuple(axes),
        filters=Filters(
            labels=_labels(get_option("labels")),
            labels_match=correspondance,
            states=_liste(get_option("states")),
            exclude_labels=_labels(exclusions.get("labels")),
            exclude_states=_liste(exclusions.get("states")),
        ),
        include_raw=bool(get_option("include_raw")),
        strict=bool(get_option("strict")),
    )
