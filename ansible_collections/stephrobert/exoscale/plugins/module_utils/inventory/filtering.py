# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Stéphane Robert
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Le filtrage qui reste à faire une fois les réponses reçues.

`list-instances` accepte un filtre `labels`, et le contrat ne dit pas s'il
applique un ET ou un OU sur plusieurs paires. Ce que le contrat ne dit pas ne
se suppose pas : le provider ne passe le filtre à l'API que pour **un** label,
où les deux lectures coïncident, et tout le reste se décide ici, sur le
modèle normalisé, par des fonctions pures.
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

    def api_labels(self) -> Mapping[str, str]:
        """Le filtre à passer à l'API, et rien d'autre.

        Un seul label, avec sa valeur : le contrat ne dit pas ce que l'API fait
        de plusieurs paires, et une clé sans valeur n'est pas un filtre qu'elle
        sait exprimer. Dans les deux autres cas on transfère, et on affine ici :
        le filtrage local ne peut pas récupérer ce qu'il n'a pas reçu.
        """
        if len(self.labels) == 1:
            ((cle, valeur),) = self.labels.items()
            if valeur:
                return {cle: valeur}
        return {}


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
