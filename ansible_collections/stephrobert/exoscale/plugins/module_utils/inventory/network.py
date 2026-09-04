# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Stéphane Robert
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""L'index réseau, et la jointure en mémoire.

**Chez Exoscale, l'adresse privée n'est pas sur l'instance.** Le schéma
`instance` porte `private-networks`, une liste de références `{id}`, et rien
d'autre ; c'est le schéma `private-network` qui porte les baux (`leases`),
chacun avec `instance-id` et `ip`. Mesuré sur le contrat versionné.

Retrouver l'adresse privée d'une machine demande donc de lire les réseaux,
pas les machines. On liste une fois par zone, on lit chaque réseau une fois,
on indexe les baux par identifiant d'instance, puis on joint :

    list-private-networks(zone)         -> les réseaux, leur nom
    get-private-network(id)             -> les baux : instance-id, ip
              |
              v
      index : instance-id -> (réseau, adresses)
              |
              v
      jointure O(machines)

Le coût est `O(zones + réseaux)` en appels, jamais `O(machines)`. C'est
moins bon que l'index régional unique de Scaleway, et c'est ce que le contrat
permet : aucune opération ne rend tous les baux d'une zone en un appel.

Ce module ne connaît pas le SDK : il travaille sur des enregistrements déjà
normalisés, ce qui le rend testable sans réseau.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from .models import NetworkAttachment


@dataclass(frozen=True)
class PrivateNetworkInfo:
    """Ce qu'on sait d'un réseau privé, réduit à ce dont la jointure a besoin."""

    id: str
    name: str | None = None


@dataclass(frozen=True)
class Lease:
    """Un bail : une adresse attribuée à une machine sur un réseau."""

    private_network_id: str
    host_id: str
    address: str

    @property
    def is_ipv6(self) -> bool:
        return ":" in self.address


@dataclass(frozen=True)
class NetworkIndex:
    """Les index construits une fois, consultés autant de fois qu'il faut."""

    leases_by_host: Mapping[str, tuple[Lease, ...]]
    networks: Mapping[str, PrivateNetworkInfo]

    @property
    def lease_count(self) -> int:
        return sum(len(v) for v in self.leases_by_host.values())


def strip_netmask(address: str) -> str:
    """`10.0.0.5/22` -> `10.0.0.5`. Un bail rend une adresse, on la garde nue."""
    return address.split("/", 1)[0]


def build_index(
    leases: tuple[Lease, ...],
    networks: tuple[PrivateNetworkInfo, ...] = (),
) -> NetworkIndex:
    """Construit les index de jointure. Une seule passe sur chaque liste."""
    par_hote: dict[str, list[Lease]] = {}
    for bail in leases:
        if not bail.host_id or not bail.address:
            continue
        par_hote.setdefault(bail.host_id, []).append(bail)

    return NetworkIndex(
        leases_by_host={
            hote: tuple(sorted(liste, key=lambda b: (b.is_ipv6, b.private_network_id, b.address)))
            for hote, liste in par_hote.items()
        },
        networks={reseau.id: reseau for reseau in networks},
    )


def attach(
    host_id: str,
    network_ids: tuple[str, ...],
    index: NetworkIndex,
) -> tuple[NetworkAttachment, ...]:
    """Joint une machine à ses réseaux avec l'index, sans appel d'API.

    Les réseaux viennent de la machine (`private-networks`), les adresses de
    l'index (les baux). Un réseau que la machine déclare sans bail reste un
    rattachement, sans adresse : la machine est bien sur ce réseau, elle n'y a
    simplement pas encore d'adresse, et le dire vaut mieux que l'oublier.
    """
    baux = index.leases_by_host.get(host_id, ())
    par_reseau: dict[str, list[Lease]] = {}
    for bail in baux:
        par_reseau.setdefault(bail.private_network_id, []).append(bail)

    # Les réseaux déclarés par la machine d'abord, puis ceux que seuls les
    # baux connaissent : la réponse de l'instance peut retarder sur le réseau.
    reseaux = list(network_ids) + [r for r in par_reseau if r not in network_ids]

    rattachements: list[NetworkAttachment] = []
    for reseau_id in reseaux:
        info = index.networks.get(reseau_id)
        adresses = par_reseau.get(reseau_id, [])
        rattachements.append(
            NetworkAttachment(
                private_network_id=reseau_id,
                private_network_name=info.name if info else None,
                ipv4=tuple(strip_netmask(b.address) for b in adresses if not b.is_ipv6),
                ipv6=tuple(strip_netmask(b.address) for b in adresses if b.is_ipv6),
            )
        )

    # Trié par nom de réseau puis par identifiant : deux exécutions doivent
    # rendre le même ordre, sur lequel la sélection d'adresse s'appuie.
    return tuple(
        sorted(
            rattachements,
            key=lambda a: (a.private_network_name or "", a.private_network_id),
        )
    )


def flatten(attachments: tuple[NetworkAttachment, ...]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Les adresses privées, tous réseaux confondus, dans l'ordre des réseaux."""
    ipv4 = tuple(adresse for a in attachments for adresse in a.ipv4)
    ipv6 = tuple(adresse for a in attachments for adresse in a.ipv6)
    return ipv4, ipv6
