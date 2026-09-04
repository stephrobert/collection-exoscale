"""Traduction du vocabulaire de l'API vers celui d'Ansible.

Trois traductions vivent ici, et une seule fois : le **nom** d'un module, le
**nom** d'une option et le **type** d'une option. Les templates ne doivent
contenir aucune des trois.

**Le nom d'option n'est pas inversé.** `disk-size` devient `disk_size`, et le
module généré porte les deux côte à côte (`OperationBinding.body_params` est
un dictionnaire option -> nom du contrat). Reconstituer `disk-size` depuis
`disk_size` serait deviner : le contrat porte 321 propriétés qui contiennent
déjà un `_`, et rien ne dit laquelle des deux formes une propriété emploie.
"""

from __future__ import annotations

import re

from generator.ir.enums import ApiType, OperationKind
from generator.ir.models import ApiParameter
from generator.parser.naming import option_name as _option_name

#: Suffixe de module par classification. `MANAGE` n'en porte aucun : le module
#: qui gère l'état durable d'une ressource porte le nom de la ressource.
_MODULE_SUFFIX: dict[OperationKind, str | None] = {
    OperationKind.INFO: "_info",
    OperationKind.ACTION: "_action",
    OperationKind.MANAGE: "",
    OperationKind.WORKFLOW: "",
}

#: Correspondance des types de l'IR vers les types `argument_spec`.
_ANSIBLE_TYPES: dict[ApiType, str] = {
    ApiType.STRING: "str",
    ApiType.INTEGER: "int",
    ApiType.NUMBER: "float",
    ApiType.BOOLEAN: "bool",
    ApiType.ENUM: "str",
    ApiType.ARRAY: "list",
    ApiType.MAP: "dict",
    ApiType.OBJECT: "dict",
}

#: Fragments de nom qui rendent un paramètre sensible. La liste est
#: volontairement large : un faux positif se corrige par un override, un faux
#: négatif écrit un secret dans le journal d'Ansible.
_SENSITIVE_FRAGMENTS: tuple[str, ...] = (
    "secret",
    "token",
    "password",
    "passphrase",
    "private_key",
    "credential",
    "api_key",
)

#: Paramètres portés par le module_utils commun : ils ne se redéclarent jamais
#: dans un module généré.
COMMON_PARAMETERS: frozenset[str] = frozenset(
    {"api_key", "api_secret", "zone", "api_url", "wait", "wait_timeout"}
)


class UnmappedType(Exception):
    """Un type de l'IR n'a pas d'équivalent `argument_spec`."""

    def __init__(self, parameter: str, type: ApiType) -> None:
        super().__init__(f"{parameter} : type {type.value} sans correspondance Ansible")
        self.parameter = parameter
        self.type = type


def module_name(product: str, resource: str, kind: OperationKind) -> str | None:
    """Nom du module Ansible, ou `None` quand la classe n'en produit pas.

    Le nom suit `<produit>_<ressource>[_info|_action]` et ne contient jamais un
    verbe HTTP : `compute_instance_info`, jamais `compute_get_instance`.

    **Le produit n'est pas redoublé.** Chez Exoscale, la plupart des produits
    préfixent leurs chemins de leur propre nom : `/sks-cluster`, `/kms-key`,
    `/iam-role`, `/dbaas-postgres`, `/block-storage-snapshot`. La ressource
    dérivée s'appelle donc `sks_cluster`, et la concaténation naïve donnait
    `sks_sks_cluster_info`, mesuré sur 11 des 13 produits non indexés. Quand
    la ressource commence par le nom du produit, le nom du module est la
    ressource seule : `sks_cluster_info`, ce qu'un opérateur aurait écrit.
    La clé d'override et le rapport gardent la ressource telle quelle ; seul
    le nom du fichier change.
    """
    suffix = _MODULE_SUFFIX.get(kind)
    if suffix is None:
        return None
    if resource == product or resource.startswith(product + "_"):
        return f"{resource}{suffix}"
    return f"{product}_{resource}{suffix}"


def option_name(parameter: ApiParameter) -> str:
    """Le nom d'option Ansible d'un paramètre du contrat : `disk-size` -> `disk_size`."""
    return _option_name(parameter.name)


def sdk_method(operation_id: str) -> str:
    """Le nom de méthode du SDK Python officiel pour un `operationId`.

    Ce n'est pas une supposition : `exoscale/api/generator.py` construit ses
    méthodes par `operation_name.replace("-", "_")` depuis le même contrat, et
    normalise ses arguments de la même façon. Une garde de test vérifie que le
    SDK installé expose bien chaque méthode qu'un module généré appelle.
    """
    return operation_id.replace("-", "_")


#: Ce qu'`ansible-test sanity` soupçonne d'être un secret, recopié de
#: `validate_modules/constants.py` (`NO_LOG_REGEX`). Un nom qui y correspond
#: sans `no_log` fait échouer `validate-modules` en `no-log-needed`, mesuré
#: sur `key` dans `sos_presigned_url_info`, qui est la clé d'un objet S3.
#: Quand le mapping a décidé que ce n'est pas un secret, il le **dit**, par
#: `no_log: False`, plutôt que de laisser sanity le supposer.
_SANITY_SUSPECTS = re.compile(r"(?:pass(?!ive)|secret|token|key)", re.IGNORECASE)


def looks_secret_to_sanity(name: str) -> bool:
    """Vrai quand `validate-modules` exigerait un `no_log` explicite sur ce nom."""
    return _SANITY_SUSPECTS.search(name) is not None


def is_sensitive(parameter: ApiParameter) -> bool:
    """Vrai quand le paramètre doit recevoir `no_log=True`.

    Un identifiant n'est jamais le secret lui-même : `ssh-key-id` désigne une
    clé, il ne la porte pas.
    """
    name = option_name(parameter)
    if name.endswith("_id"):
        return False
    return any(fragment in name for fragment in _SENSITIVE_FRAGMENTS)


def argument_spec_entry(parameter: ApiParameter) -> dict[str, object]:
    """Traduit un paramètre de l'IR en entrée d'`argument_spec`.

    Lève `UnmappedType` plutôt que de deviner : un type inconnu doit remonter
    dans le rapport, pas devenir un `str` par défaut.

    `required` vient du contrat quand il le déclare. Mesuré : 64 corps sur 142
    portent une liste `required`, et `scale-instance` exige `instance-type`.
    C'est une information que Scaleway ne publie pas, et il serait absurde de
    ne pas s'en servir.
    """
    ansible_type = _ANSIBLE_TYPES.get(parameter.type)
    if ansible_type is None:
        raise UnmappedType(parameter=option_name(parameter), type=parameter.type)

    entry: dict[str, object] = {"type": ansible_type}
    if parameter.required:
        entry["required"] = True
    if parameter.type is ApiType.ENUM and parameter.enum_values:
        entry["choices"] = list(parameter.enum_values)
    if parameter.type is ApiType.ARRAY:
        element = _ANSIBLE_TYPES.get(parameter.item_type or ApiType.STRING, "str")
        entry["elements"] = element
    if parameter.default is not None and parameter.type is not ApiType.ENUM:
        entry["default"] = parameter.default
    if is_sensitive(parameter):
        entry["no_log"] = True
    elif looks_secret_to_sanity(option_name(parameter)):
        entry["no_log"] = False
    return entry
