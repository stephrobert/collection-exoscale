"""Classification d'une opération de l'API v2 d'Exoscale en intention Ansible.

Le classifieur répond à une seule question : *qu'est-ce que cette opération est
pour un utilisateur Ansible ?* Il ne décide ni du nom du module, ni de son
contenu.

Deux principes gouvernent ce fichier :

* **aucune opération ne disparaît.** Ce que les règles ne savent pas trancher
  est classé `UNKNOWN`, apparaît dans le rapport, et fait échouer la CI tant
  que personne ne l'a tranché par un override ;
* **les règles sont mécaniques et peu nombreuses.** Une règle qui aurait besoin
  de connaître une opération en particulier n'est pas une règle : c'est un
  override, et il se déclare dans `generator/overrides/`.

**Ces règles ne sont pas celles de Scaleway, et c'est mesuré.** Les six règles
de Scaleway appliquées telles quelles aux 374 opérations d'Exoscale laissent
58 UNKNOWN, parce qu'Exoscale porte ses actions sur **PUT** (`start-instance`,
`scale-instance`, `attach-instance-to-private-network`, `rotate-sks-*`) et
remet un champ à zéro par un **DELETE** (`reset-instance-field`). Chez
Scaleway, PUT voulait dire « remplacement complet » et DELETE « suppression » ;
chez Exoscale, c'est le verbe de l'`operationId` qui porte le sens, et la
méthode ne fait que confirmer.

| verbe | méthode | classe | ce que ça veut dire |
|---|---|---|---|
| `get`, `list` | GET | INFO | lecture |
| `reveal` | GET | INFO | lecture d'un secret : la valeur rendue est sensible |
| `get`, `list` | POST | INFO | lecture dont le corps décrit la requête |
| `create` | POST | LIFECYCLE | création, périmètre Terraform |
| `delete` | DELETE | LIFECYCLE | suppression, périmètre Terraform |
| `reset` | DELETE | ACTION | remise d'un champ à sa valeur par défaut |
| `update` | PUT, PATCH, POST | MANAGE | écriture d'un état durable |
| autre | PUT, POST | ACTION | opération ponctuelle sur l'existant |
| autre | autre | **UNKNOWN** | |

Mesuré sur le contrat entier après ces règles : zéro UNKNOWN. Ce n'est pas une
preuve qu'elles ont raison, seulement qu'elles ont décidé, et c'est pourquoi le
rapport affiche la raison de chaque décision.
"""

from __future__ import annotations

from dataclasses import dataclass

from generator.ir.enums import DAY2_KINDS, GenerationMode, HTTPMethod, OperationKind
from generator.ir.models import ApiOperation
from generator.parser.naming import split_words

#: Verbes de lecture. Exoscale préfixe systématiquement ses `operationId`.
_READ_VERBS: frozenset[str] = frozenset({"get", "list"})

#: Lecture d'un secret : `reveal-instance-password`, `reveal-*-api-key`.
_REVEAL_VERBS: frozenset[str] = frozenset({"reveal"})

#: Verbes de création et de suppression : la responsabilité de Terraform.
_CREATE_VERBS: frozenset[str] = frozenset({"create"})
_DELETE_VERBS: frozenset[str] = frozenset({"delete"})

#: Remise d'un champ à sa valeur par défaut, portée par DELETE sur `{field}`.
#: Le contrat le dit lui-même : « Reset an Instance Pool field to its default
#: value ». Rien n'est supprimé.
_RESET_VERBS: frozenset[str] = frozenset({"reset"})

#: Écriture d'un état durable.
_UPDATE_VERBS: frozenset[str] = frozenset({"update"})

#: Méthodes qui portent une écriture chez Exoscale. PUT y porte des actions
#: (52 sur 89) autant que des mises à jour (37), d'où le verbe qui tranche.
_WRITE_METHODS: frozenset[HTTPMethod] = frozenset({HTTPMethod.PUT, HTTPMethod.POST})


@dataclass(frozen=True)
class Classification:
    """Décision de classification d'une opération, avec sa justification."""

    key: str
    kind: OperationKind
    mode: GenerationMode
    #: Règle ou override qui a produit la décision, affiché dans le rapport.
    reason: str

    @property
    def is_day2(self) -> bool:
        return self.kind in DAY2_KINDS


def verb_of(operation: ApiOperation) -> str:
    """Premier mot de l'`operationId`, en minuscules : `start-instance` -> `start`."""
    words = split_words(operation.id)
    return words[0] if words else ""


def classify(operation: ApiOperation) -> Classification:
    """Classe une opération à partir de son verbe et de sa méthode HTTP."""
    verb = verb_of(operation)
    method = operation.http_method

    if verb in _READ_VERBS and method is HTTPMethod.GET:
        return _decision(operation, OperationKind.INFO, "verbe de lecture sur GET")

    if verb in _REVEAL_VERBS and method is HTTPMethod.GET:
        return _decision(
            operation,
            OperationKind.INFO,
            "révélation d'un secret sur GET : une lecture, dont la valeur rendue est sensible",
        )

    if verb in _READ_VERBS and method is HTTPMethod.POST:
        return _decision(
            operation,
            OperationKind.INFO,
            "lecture portée par POST : le corps décrit la requête, rien n'est écrit",
        )

    if verb in _CREATE_VERBS and method is HTTPMethod.POST:
        return _decision(
            operation, OperationKind.LIFECYCLE, "création de ressource, périmètre Terraform"
        )

    if verb in _DELETE_VERBS and method is HTTPMethod.DELETE:
        return _decision(
            operation, OperationKind.LIFECYCLE, "suppression de ressource, périmètre Terraform"
        )

    if verb in _RESET_VERBS and method is HTTPMethod.DELETE:
        return _decision(
            operation,
            OperationKind.ACTION,
            "remise d'un champ à sa valeur par défaut : DELETE sur un champ, pas sur la ressource",
        )

    if verb in _UPDATE_VERBS and method in (HTTPMethod.PUT, HTTPMethod.PATCH, HTTPMethod.POST):
        if method is HTTPMethod.POST:
            return _decision(
                operation,
                OperationKind.MANAGE,
                "écriture d'un état durable, portée par POST (« Update/Create »)",
            )
        return _decision(operation, OperationKind.MANAGE, "écriture d'un état durable")

    if method in _WRITE_METHODS:
        return _decision(
            operation,
            OperationKind.ACTION,
            f"verbe d'action {verb!r} sur {method.value} : opération ponctuelle sur l'existant",
        )

    return _decision(
        operation,
        OperationKind.UNKNOWN,
        f"aucune règle pour {method.value} avec le verbe {verb!r}",
    )


def _decision(operation: ApiOperation, kind: OperationKind, reason: str) -> Classification:
    return Classification(key=operation.key, kind=kind, mode=GenerationMode.AUTO, reason=reason)
