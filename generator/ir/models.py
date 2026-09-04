"""Représentation intermédiaire canonique d'un produit de l'API v2 d'Exoscale.

Ce modèle est volontairement indépendant :

* de la source (OpenAPI 3.0 aujourd'hui, autre chose demain) ;
* du SDK Exoscale utilisé au runtime ;
* d'Ansible.

Il conserve assez d'information pour détecter la dérive d'API : descriptions,
dépréciations, valeurs d'enum et formes de réponse sont portées par l'IR même
quand la génération ne s'en sert pas encore.

Les dataclasses sont gelées et les collections sont des tuples : une IR
immuable se compare, se hache et se sérialise sans surprise, ce qui est la
condition d'une génération déterministe.

Deux champs n'ont pas d'équivalent chez Scaleway, et ils sont mesurés :

* `ApiResponse.is_operation` : 203 écritures sur 374 répondent par un objet
  `operation` asynchrone. Un module qui rend `changed` sans attendre sa fin
  ment, et c'est l'IR qui porte le fait pour que le runtime le traite ;
* `ApiParameter.read_only` : le contrat marque `readOnly` 169 propriétés. Une
  propriété en lecture seule ne se déclare pas dans un `argument_spec`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from generator.ir.enums import ApiType, HTTPMethod, ParameterLocation


@dataclass(frozen=True)
class ApiEnum:
    """Enum nommé du contrat, référencé par un ou plusieurs paramètres."""

    name: str
    values: tuple[str, ...]
    default: str | None = None
    description: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return _compact(
            {
                "name": self.name,
                "values": list(self.values),
                "default": self.default,
                "description": self.description,
            }
        )


@dataclass(frozen=True)
class ApiParameter:
    """Paramètre d'entrée d'une opération, quelle que soit sa position.

    `name` est le nom **du contrat**, en kebab-case (`disk-size`). La
    traduction vers un nom d'option Ansible est une décision du mapping, et
    l'IR ne la prend pas : garder le nom d'origine est ce qui permet au
    runtime d'envoyer le bon nom sans rien reconstituer.
    """

    name: str
    type: ApiType
    required: bool
    location: ParameterLocation
    description: str | None = None
    enum_name: str | None = None
    enum_values: tuple[str, ...] = ()
    item_type: ApiType | None = None
    default: object | None = None
    deprecated: bool = False
    format: str | None = None
    #: Nom du schéma référencé quand le paramètre porte une structure imbriquée.
    ref: str | None = None
    #: Vrai quand le contrat marque la propriété `readOnly`.
    read_only: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _compact(
            {
                "name": self.name,
                "type": self.type.value,
                "required": self.required,
                "location": self.location.value,
                "description": self.description,
                "enum_name": self.enum_name,
                "enum_values": list(self.enum_values) or None,
                "item_type": self.item_type.value if self.item_type else None,
                "default": self.default,
                "deprecated": self.deprecated or None,
                "format": self.format,
                "ref": self.ref,
                "read_only": self.read_only or None,
            }
        )


@dataclass(frozen=True)
class ApiResponse:
    """Forme de la réponse de succès d'une opération."""

    #: Nom du schéma de réponse tel que déclaré par le contrat, s'il est nommé.
    schema: str | None = None
    #: Champ portant la ressource utile (`instances`, `instance-types`, ...).
    payload_field: str | None = None
    #: Nom du schéma de la ressource portée par `payload_field`.
    payload_schema: str | None = None
    #: Vrai quand la charge utile est une liste.
    is_list: bool = False
    #: Vrai quand la réponse est l'objet `operation` : l'appel est asynchrone,
    #: et son résultat se lit en interrogeant l'opération jusqu'à `success`.
    is_operation: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _compact(
            {
                "schema": self.schema,
                "payload_field": self.payload_field,
                "payload_schema": self.payload_schema,
                "is_list": self.is_list or None,
                "is_operation": self.is_operation or None,
            }
        )


@dataclass(frozen=True)
class ApiOperation:
    """Une opération du contrat, dans le vocabulaire de l'API et non d'Ansible."""

    #: Identifiant du contrat, ex. `start-instance`.
    id: str
    product: str
    version: str
    #: Ressource déduite du chemin, en snake_case singulier, ex. `instance`.
    resource: str
    http_method: HTTPMethod
    path: str
    parameters: tuple[ApiParameter, ...] = ()
    response: ApiResponse | None = None
    summary: str | None = None
    description: str | None = None
    deprecated: bool = False
    tags: tuple[str, ...] = ()

    @property
    def key(self) -> str:
        """Clé stable d'une opération, utilisée par les overrides et le rapport.

        Format : `<produit>.<version>.<Ressource>.<operation-id>`, ex.
        `compute.v2.Instance.start-instance`.
        """
        resource = "".join(part.capitalize() for part in self.resource.split("_"))
        return f"{self.product}.{self.version}.{resource}.{self.id}"

    @property
    def is_async(self) -> bool:
        """Vrai quand l'appel rend un objet `operation` à surveiller."""
        return self.response is not None and self.response.is_operation

    def parameter(self, name: str) -> ApiParameter | None:
        for parameter in self.parameters:
            if parameter.name == name:
                return parameter
        return None

    def to_dict(self) -> dict[str, Any]:
        return _compact(
            {
                "key": self.key,
                "id": self.id,
                "product": self.product,
                "version": self.version,
                "resource": self.resource,
                "http_method": self.http_method.value,
                "path": self.path,
                "summary": self.summary,
                "description": self.description,
                "deprecated": self.deprecated or None,
                "tags": list(self.tags) or None,
                "parameters": [p.to_dict() for p in self.parameters] or None,
                "response": self.response.to_dict() if self.response else None,
            }
        )


@dataclass(frozen=True)
class ApiService:
    """Un produit Exoscale dans une version donnée, ex. `compute` v2.

    Un produit n'est pas un fichier : c'est une famille de tags découpée dans
    le document unique que publie Exoscale. Voir `generator/source/base.py`.
    """

    name: str
    version: str
    title: str | None = None
    description: str | None = None
    source: str | None = None
    #: Zones déclarées par la variable `{zone}` de l'URL du serveur.
    zones: tuple[str, ...] = ()
    operations: tuple[ApiOperation, ...] = ()
    enums: tuple[ApiEnum, ...] = ()
    #: Anomalies rencontrées au parsing, remontées telles quelles dans le rapport.
    warnings: tuple[str, ...] = field(default=(), compare=False)

    @property
    def slug(self) -> str:
        return f"{self.name}.{self.version}"

    def operation(self, operation_id: str) -> ApiOperation | None:
        for operation in self.operations:
            if operation.id == operation_id:
                return operation
        return None

    def to_dict(self) -> dict[str, Any]:
        return _compact(
            {
                "product": self.name,
                "version": self.version,
                "title": self.title,
                "description": self.description,
                "source": self.source,
                "zones": list(self.zones) or None,
                "enums": [e.to_dict() for e in self.enums] or None,
                "operations": [o.to_dict() for o in self.operations] or None,
                "warnings": list(self.warnings) or None,
            }
        )

    def to_json(self) -> str:
        """Sérialisation déterministe, utilisée par les golden tests."""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False, sort_keys=False) + "\n"


def _compact(data: dict[str, Any]) -> dict[str, Any]:
    """Retire les clés nulles pour que l'IR sérialisée reste lisible en diff."""
    return {key: value for key, value in data.items() if value is not None}
