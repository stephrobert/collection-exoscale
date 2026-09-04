# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Stéphane Robert
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Les groupes natifs, et l'assainissement de leurs noms.

Une seule implémentation de l'assainissement, ici, testée. Ansible accepte
pour un nom de groupe les lettres, les chiffres et le tiret bas, et refuse un
nom qui commence par un chiffre ; un label `env=pré-prod` doit donner un
groupe lisible sans casser l'inventaire.
"""

from __future__ import annotations

import re
import unicodedata

from .models import InventoryHost

#: Ce que `group_by` accepte. Un axe absent de cette table est une faute de
#: configuration, pas un groupe vide créé en silence.
AXES: tuple[str, ...] = (
    "product",
    "zone",
    "state",
    "labels",
    "private_network",
    "manager",
    "type",
)

#: Préfixe des groupes produits par le plugin, pour qu'ils ne se confondent
#: pas avec ceux qu'un `keyed_groups` de l'utilisateur crée.
PREFIX = "exo"

_INVALIDES = re.compile(r"[^A-Za-z0-9_]+")


def sanitize_group_name(raw: str, fallback: str = "inconnu") -> str:
    """Rend un nom de groupe valide pour Ansible, de façon déterministe.

    Les accents sont dépliés plutôt que supprimés : `pré-prod` devient
    `pre_prod` et non `pr_prod`, ce qui reste lisible pour qui écrit le
    playbook.
    """
    texte = unicodedata.normalize("NFKD", str(raw))
    texte = texte.encode("ascii", "ignore").decode("ascii")
    texte = _INVALIDES.sub("_", texte).strip("_")
    texte = re.sub(r"_{2,}", "_", texte)

    if not texte:
        return fallback
    if texte[0].isdigit():
        return f"_{texte}"
    return texte


def group_names(host: InventoryHost, axes: tuple[str, ...]) -> tuple[str, ...]:
    """Les groupes auxquels cette machine appartient, selon les axes demandés.

    Un label donne un groupe par paire (`exo_label_env_prod`) : c'est la clé
    **et** la valeur qui font le sens, `env=prod` et `env=staging` n'ont rien
    en commun. Le gestionnaire donne un groupe par type et un par identifiant,
    pour cibler « tous les membres de pools » comme « les membres de ce pool ».
    """
    noms: list[str] = []

    for axe in axes:
        if axe == "product" and host.product:
            noms.append(f"{PREFIX}_product_{sanitize_group_name(host.product)}")
        elif axe == "zone" and host.zone:
            noms.append(f"{PREFIX}_zone_{sanitize_group_name(host.zone)}")
        elif axe == "state" and host.state:
            noms.append(f"{PREFIX}_state_{sanitize_group_name(host.state)}")
        elif axe == "labels":
            noms.extend(
                f"{PREFIX}_label_{sanitize_group_name(cle)}_{sanitize_group_name(valeur)}"
                for cle, valeur in host.labels.items()
                if cle
            )
        elif axe == "private_network":
            noms.extend(
                f"{PREFIX}_private_network_"
                f"{sanitize_group_name(a.private_network_name or a.private_network_id)}"
                for a in host.private_networks
            )
        elif axe == "manager" and host.manager_type:
            noms.append(f"{PREFIX}_manager_{sanitize_group_name(host.manager_type)}")
            if host.manager_id:
                noms.append(f"{PREFIX}_manager_{sanitize_group_name(host.manager_id)}")
        elif axe == "type" and host.metadata.get("type"):
            noms.append(f"{PREFIX}_type_{sanitize_group_name(str(host.metadata['type']))}")

    # Trié et dédoublonné : deux exécutions doivent produire le même inventaire.
    return tuple(sorted(set(noms)))
