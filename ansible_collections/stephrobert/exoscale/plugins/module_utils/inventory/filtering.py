# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Stéphane Robert
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Le filtrage qui reste à faire une fois les réponses reçues.

`list-instances` déclare un filtre `labels` que le contrat type en chaîne nue,
sans format : le provider ne le passe jamais à l'API, et tout se décide ici,
sur le modèle normalisé, par des fonctions pures.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Filters:
    """Ce que l'utilisateur garde, et ce qu'il écarte."""

    #: Les labels demandés, clé et valeur. Une valeur vide veut dire « la clé
    #: existe, quelle que soit sa valeur ».
    labels: Mapping[str, str] = field(default_factory=dict)
    labels_match: str = "any"
    states: tuple[str, ...] = ()
    exclude_labels: Mapping[str, str] = field(default_factory=dict)
    exclude_states: tuple[str, ...] = ()


def _matches(labels: Mapping[str, str], cle: str, valeur: str) -> bool:
    """Vrai quand la machine porte ce label, à cette valeur ou à n'importe laquelle."""
    if cle not in labels:
        return False
    return not valeur or str(labels[cle]) == valeur


def keep(labels: Mapping[str, str], state: str | None, filters: Filters) -> tuple[bool, str]:
    """Garde-t-on cette machine, et sinon pourquoi.

    La raison est rendue pour que le mode debug puisse répondre à « pourquoi
    cette machine n'apparaît-elle pas ». Les arguments sont les champs et non
    la machine : la fonction ne dépend d'aucun produit.
    """
    for cle, valeur in filters.exclude_labels.items():
        if _matches(labels, cle, valeur):
            return (
                False,
                f"exclue par le label '{cle}={valeur}'"
                if valeur
                else f"exclue par le label '{cle}'",
            )

    if state and state in filters.exclude_states:
        return False, f"exclue par l'état '{state}'"

    if filters.states and (state or "") not in filters.states:
        return False, f"état '{state}' hors de {list(filters.states)}"

    if filters.labels:
        verdicts = {cle: _matches(labels, cle, valeur) for cle, valeur in filters.labels.items()}
        if filters.labels_match == "all":
            manquants = sorted(cle for cle, ok in verdicts.items() if not ok)
            if manquants:
                return False, f"labels manquants {manquants}"
        elif not any(verdicts.values()):
            return False, f"aucun des labels {sorted(filters.labels)}"

    return True, "retenue"
