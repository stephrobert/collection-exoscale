# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Stéphane Robert
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Ce qu'un provider doit savoir faire, et ce qu'il ne doit pas faire.

**Un provider ne touche jamais à l'objet d'inventaire d'Ansible.** Il rend un
`ProviderResult` ; c'est le moteur qui décide ensuite quoi en faire. Sans cette
règle, ajouter un produit demanderait de toucher au cœur.

**Un provider n'importe pas le SDK.** Il reçoit une fabrique de clients, un
par zone, qui expose les méthodes dont il a besoin. Un test lui passe un objet
qui rend des réponses figées, et la normalisation se mesure sans réseau ni
identifiants.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from ..models import ProviderResult

#: Les zones Exoscale, mesurées sur l'énumération `zone` du serveur du contrat
#: versionné (`servers[0].variables.zone.enum`). Un test les confronte au
#: contrat : une zone ajoutée en amont fait rougir la CI plutôt que manquer
#: à l'inventaire en silence.
EXOSCALE_ZONES: tuple[str, ...] = (
    "ch-gva-2",
    "ch-dk-2",
    "de-fra-1",
    "de-muc-1",
    "at-vie-1",
    "at-vie-2",
    "bg-sof-1",
    "hr-zag-1",
)


@dataclass(frozen=True)
class DiscoveryContext:
    """Ce que l'utilisateur a demandé, tel qu'un provider en a besoin."""

    zones: tuple[str, ...] = ()
    #: Le filtre de labels que l'API sait appliquer, déjà réduit.
    api_labels: Mapping[str, str] | None = None
    include_raw: bool = False
    #: Les index réseau, par zone, construits une fois pour tous les providers.
    network: Mapping[str, Any] | None = None

    def scoped_zones(self, available: tuple[str, ...]) -> tuple[str, ...]:
        """Les zones à interroger : celles demandées, sinon celles du contrat."""
        if not self.zones:
            return available
        return tuple(zone for zone in self.zones if zone in available)


#: Une fabrique de client : une zone, un client qui parle à cette zone.
ClientFactory = Callable[[str], Any]


class InventoryProvider(Protocol):
    """L'interface qu'un produit doit remplir pour entrer dans l'inventaire."""

    name: str

    #: Vrai quand le produit porte des réseaux privés à joindre avec les baux.
    #: C'est le provider qui le déclare, parce que c'est lui qui sait.
    joins_private_networks: bool

    def discover(self, context: DiscoveryContext) -> ProviderResult:
        """Découvre les machines de ce produit et rend un résultat.

        Le corps est une docstring et non le `...` habituel d'un `Protocol` :
        `ansible-test sanity` refuse `def f(): ...` en E704 sur ansible-core
        2.17 et 2.18, que `meta/runtime.yml` déclare supporter.
        """
