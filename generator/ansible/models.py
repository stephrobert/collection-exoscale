"""Modèle intermédiaire d'un module Ansible, construit depuis le plan.

C'est **la seule source** de l'`argument_spec`, de la `DOCUMENTATION`, des
`EXAMPLES` et du `RETURN` d'un module. Ce fichier porte les décisions ; le
renderer ne fait que les écrire. La règle qui tranche les cas limites : **si un
template a besoin d'un `if` sur autre chose qu'une présence de valeur, la
décision manque ici.**

Trois décisions propres à Exoscale valent d'être lues avant le code :

* **une action est une opération, pas une valeur d'enum.** Scaleway expose
  `ServerAction` avec un champ `action` ; Exoscale expose `start-instance`,
  `stop-instance`, `scale-instance`, chacune avec son propre corps. Le module
  d'action d'une ressource regroupe donc plusieurs opérations, et le nom de
  l'action est **calculé** : les mots de l'`operationId` privés de ceux de la
  ressource (`resize-instance-disk` -> `resize_disk`). Un paramètre que le
  contrat exige pour une action et pas pour une autre devient un
  `required_if` sur cette action, jamais un `required` global ;
* **l'appel est asynchrone, et le module le dit.** L'objet `operation` rendu
  par l'API est porté par le binding (`is_async`), le runtime l'attend quand
  `wait` est vrai, et le retour du module l'expose ;
* **un paramètre sans type ne se rend pas.** Le contrat tait le type de 44
  paramètres de chemin ; un module qui en dépend est écarté avec sa raison
  tant qu'un override ne l'a pas typé.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from generator.ansible.collection import Collection
from generator.ansible.mapping import (
    COMMON_PARAMETERS,
    UnmappedType,
    argument_spec_entry,
    option_name,
    sdk_method,
)
from generator.ir.enums import ApiType, HTTPMethod, OperationKind, ParameterLocation
from generator.ir.models import ApiOperation, ApiParameter
from generator.overrides.loader import OperationOverride, OverrideSet, ParameterOverride
from generator.parser.naming import pluralize_phrase, split_words
from generator.plan import OperationPlan, ProductPlan

#: Classes que le renderer sait produire aujourd'hui. Une classe absente n'est
#: pas ignorée : elle est rendue dans le rapport de génération avec sa raison.
RENDERABLE_KINDS: frozenset[OperationKind] = frozenset({OperationKind.INFO, OperationKind.ACTION})

#: Ce qu'on écrit quand le contrat ne décrit pas un paramètre.
UNDOCUMENTED = "Not documented by the Exoscale API contract."

#: Identifiant d'exemple. Un exemple montre une forme, pas une ressource.
EXAMPLE_ID = "11111111-2222-3333-4444-555555555555"

#: Préfixes d'`operationId` dont la valeur rendue est un secret. `reveal-*`
#: par construction ; `generate-*` mesuré sur le contrat :
#: `generate-sks-cluster-kubeconfig` rend des identifiants signés par le
#: cluster, `generate-data-key` du matériel de clé.
SENSITIVE_READ_PREFIXES: tuple[str, ...] = ("reveal-", "generate-")


class ModuleModelError(ValueError):
    """Le plan ne permet pas de construire un module cohérent."""


class UnsupportedKind(ModuleModelError):
    """La classe d'opération n'a pas encore de renderer."""


class AmbiguousModule(ModuleModelError):
    """Les opérations d'un module ne composent pas une forme connue."""


class ConflictingOption(ModuleModelError):
    """Deux paramètres se traduisent vers la même option, ou avec des types différents."""


class UntypedParameter(ModuleModelError):
    """Le contrat tait le type d'un paramètre, et aucun override ne le dit."""


@dataclass(frozen=True)
class OperationBinding:
    """Ce que le runtime doit savoir pour appeler une opération.

    Chaque dictionnaire va de l'option Ansible (`disk_size`) au nom du contrat
    (`disk-size`). Le runtime envoie le nom du contrat ; il ne le reconstitue
    jamais.
    """

    id: str
    method: str
    http_method: str
    path: str
    path_params: dict[str, str]
    query_params: dict[str, str]
    body_params: dict[str, str]
    payload_field: str | None = None
    is_list: bool = False
    is_async: bool = False


@dataclass(frozen=True)
class ActionBinding:
    """Une action d'un module d'action : son nom, et l'opération qu'elle appelle."""

    name: str
    operation: OperationBinding
    #: Options que le contrat exige pour cette action seule.
    required: tuple[str, ...] = ()
    #: État de la ressource attendu une fois l'opération terminée, s'il est décidé.
    expected_state: str | None = None
    #: Vrai quand l'action agit même si l'état attendu est déjà atteint.
    always_acts: bool = False


@dataclass(frozen=True)
class AnsibleModuleSpec:
    """Tout ce qu'un module généré contient, décidé une fois."""

    name: str
    kind: OperationKind
    product: str
    resource: str
    collection: Collection
    options: dict[str, dict[str, Any]]
    option_docs: dict[str, str]
    get_operation: OperationBinding | None = None
    list_operation: OperationBinding | None = None
    selector: str | None = None
    actions: tuple[ActionBinding, ...] = ()
    state_field: str | None = None
    #: La lecture unitaire de la ressource, quand un état est attendu : c'est
    #: elle qui sépare « l'API a accepté » de « la machine tourne ».
    read_operation: OperationBinding | None = None
    #: Limites du contrat rencontrées en construisant le module.
    limits: tuple[str, ...] = ()
    sensitive_return: bool = False
    summary: str | None = None

    @property
    def operation_ids(self) -> tuple[str, ...]:
        ids = [op.id for op in (self.get_operation, self.list_operation) if op is not None]
        ids.extend(action.operation.id for action in self.actions)
        return tuple(ids)

    @property
    def waitable(self) -> bool:
        return any(action.operation.is_async for action in self.actions)

    @property
    def has_synchronous(self) -> bool:
        """Vrai quand une action répond tout de suite, par sa réponse et non par
        une opération : `enable-kms-key`, `resize-block-storage-volume`."""
        return any(not action.operation.is_async for action in self.actions)

    @property
    def resource_words(self) -> str:
        return self.resource.replace("_", " ")

    def argument_spec(self) -> dict[str, dict[str, Any]]:
        return dict(self.options)

    def required_if(self) -> list[tuple[str, str, list[str]]]:
        return [
            ("action", action.name, list(action.required))
            for action in self.actions
            if action.required
        ]

    def documentation(self) -> dict[str, Any]:
        """Le bloc `DOCUMENTATION`, dans l'ordre d'une lecture humaine."""
        options: dict[str, Any] = {}
        for name, entry in self.options.items():
            option: dict[str, Any] = {"description": self.option_docs.get(name, UNDOCUMENTED)}
            option["type"] = entry["type"]
            if entry.get("required"):
                option["required"] = True
            if "choices" in entry:
                option["choices"] = list(entry["choices"])
            if "elements" in entry:
                option["elements"] = entry["elements"]
            if "default" in entry:
                option["default"] = entry["default"]
            options[name] = option

        notes: list[str] = []
        if self.kind is OperationKind.ACTION and self.waitable and not self.has_synchronous:
            notes.append(
                "Every action is asynchronous on the Exoscale API: the module waits for "
                "the returned operation to reach C(success) when I(wait) is true, and "
                "returns the operation as accepted otherwise."
            )
        elif self.kind is OperationKind.ACTION and self.waitable:
            notes.append(
                "Actions that answer with an operation are waited for until C(success) "
                "when I(wait) is true, and returned as accepted otherwise; the other "
                "actions answer at once, and their response is returned under RV(result)."
            )
        elif self.kind is OperationKind.ACTION:
            notes.append(
                "Every action of this module answers at once: the API response is "
                "returned under RV(result), and there is nothing to wait for."
            )
        if self.sensitive_return:
            notes.append("The returned value is a secret: do not log the task output.")
        if self.read_operation is not None and self.state_field is not None:
            expected = ", ".join(
                f"C({action.name}) leads to C({action.expected_state})"
                for action in self.actions
                if action.expected_state is not None
            )
            always = ", ".join(f"C({action.name})" for action in self.actions if action.always_acts)
            notes.append(
                f"Once the operation succeeds, the module reads the {self.resource_words} "
                f"until its C({self.state_field}) reaches the expected value ({expected}), "
                f"and reports C(changed=false) without sending anything when the "
                f"{self.resource_words} already is in that state"
                + (f", except for {always}, which always acts." if always else ".")
            )

        document: dict[str, Any] = {
            "module": self.name,
            "short_description": self.short_description(),
            "version_added": self.collection.version,
            "description": [self.long_description()],
            "author": list(self.collection.authors) or [self.collection.fqcn],
            "options": options,
            "extends_documentation_fragment": self.doc_fragments(),
        }
        if notes:
            document["notes"] = notes
        return document

    def doc_fragments(self) -> list[str]:
        """Le fragment commun, et celui de l'attente quand le module attend."""
        fragments = [self.collection.doc_fragment]
        if self.waitable:
            fragments.append(f"{self.collection.doc_fragment}.wait")
        return fragments

    def short_description(self) -> str:
        if self.kind is OperationKind.INFO:
            return f"Gather information about Exoscale {pluralize_phrase(self.resource)}"
        return f"Perform an action on an Exoscale {self.resource_words}"

    def long_description(self) -> str:
        if self.kind is OperationKind.INFO:
            if self.list_operation is None:
                return (
                    f"Read one Exoscale {self.resource_words}. This module never changes anything."
                )
            if self.get_operation is None:
                return (
                    f"List Exoscale {pluralize_phrase(self.resource)}. "
                    "This module never changes anything."
                )
            return (
                f"Read one Exoscale {self.resource_words} by its identifier, "
                f"or list them. This module never changes anything."
            )
        names = ", ".join(f"C({action.name})" for action in self.actions)
        return (
            f"Trigger one of the following actions on an existing {self.resource_words}: {names}."
        )

    def examples_documentation(self) -> list[dict[str, Any]]:
        fqcn = self.collection.module_fqcn(self.name)
        if self.kind is OperationKind.INFO:
            examples: list[dict[str, Any]] = []
            if self.list_operation is not None:
                examples.append(
                    {
                        "name": f"List {pluralize_phrase(self.resource)}",
                        fqcn: {"zone": "ch-gva-2"},
                        "register": "result",
                    }
                )
            if self.get_operation is not None:
                # Le sélecteur quand il y en a un, sinon chaque identifiant de
                # chemin de la lecture : ils sont tous obligatoires.
                identifiers = (
                    [self.selector]
                    if self.selector is not None
                    else sorted(self.get_operation.path_params)
                )
                examples.append(
                    {
                        "name": f"Read one {self.resource_words}",
                        fqcn: {"zone": "ch-gva-2", **{name: EXAMPLE_ID for name in identifiers}},
                        "register": "result",
                    }
                )
            return examples
        first = self.actions[0]
        task: dict[str, Any] = {"zone": "ch-gva-2", "action": first.name}
        for name, entry in self.options.items():
            if name != "action" and entry.get("required"):
                task[name] = EXAMPLE_ID
        return [{"name": f"Run {first.name} on a {self.resource_words}", fqcn: task}]

    def return_documentation(self) -> dict[str, Any]:
        if self.kind is OperationKind.INFO:
            plural = pluralize_phrase(self.resource).replace(" ", "_")
            returned: dict[str, Any] = {}
            both = self.get_operation is not None and self.list_operation is not None
            if self.get_operation is not None:
                returned[self.resource] = {
                    "description": (
                        f"The {self.resource_words}, when a selector is given."
                        if both
                        else f"The {self.resource_words}."
                    ),
                    "returned": "when the selector is given" if both else "always",
                    "type": "dict",
                }
            if self.list_operation is not None:
                returned[plural] = {
                    "description": f"The {pluralize_phrase(self.resource)}.",
                    "returned": "when no selector is given" if both else "always",
                    "type": "list",
                    "elements": "dict",
                }
            return returned
        returned = {}
        if self.waitable:
            returned["operation"] = {
                "description": (
                    "The Exoscale operation object: its C(state) is C(success) once "
                    "the work is done, C(pending) when the module did not wait."
                ),
                "returned": "for asynchronous actions" if self.has_synchronous else "always",
                "type": "dict",
            }
        if self.read_operation is not None and self.state_field is not None:
            returned[self.state_field] = {
                "description": (
                    f"The C({self.state_field}) of the {self.resource_words}, read after "
                    "the operation."
                ),
                "returned": "when an expected state is declared for the action",
                "type": "str",
            }
        if self.has_synchronous:
            returned["result"] = {
                "description": (
                    "The API response of an action that answers at once, with its "
                    "result rather than with an operation to wait for."
                ),
                "returned": "for synchronous actions" if self.waitable else "always",
                "type": "dict",
            }
        return returned


def build_module_specs(
    plan: ProductPlan,
    collection: Collection,
    *,
    only: tuple[str, ...] = (),
) -> tuple[tuple[AnsibleModuleSpec, ...], list[tuple[str, str]]]:
    """Construit un modèle par module du plan, et dit ce qui n'a pas pu l'être."""
    specs: list[AnsibleModuleSpec] = []
    skipped: list[tuple[str, str]] = []
    for name, operations in plan.modules().items():
        if only and name not in only:
            skipped.append((name, "hors du périmètre demandé"))
            continue
        try:
            specs.append(_build_spec(name, operations, plan, collection))
        except ModuleModelError as error:
            skipped.append((name, str(error)))
    return tuple(specs), skipped


def _build_spec(
    name: str,
    operations: tuple[OperationPlan, ...],
    plan: ProductPlan,
    collection: Collection,
) -> AnsibleModuleSpec:
    kinds = {item.kind for item in operations}
    if len(kinds) != 1:
        raise AmbiguousModule(f"{name} : classes mêlées {sorted(k.value for k in kinds)}")
    kind = kinds.pop()
    if kind not in RENDERABLE_KINDS:
        raise UnsupportedKind(f"{name} : la classe {kind.value.upper()} n'a pas encore de renderer")
    if kind is OperationKind.INFO:
        return _build_info_spec(name, operations, plan, collection)
    return _build_action_spec(name, operations, plan, collection)


def _build_info_spec(
    name: str,
    operations: tuple[OperationPlan, ...],
    plan: ProductPlan,
    collection: Collection,
) -> AnsibleModuleSpec:
    """Un module d'information fusionne le GET et le LIST d'une ressource."""
    gets = [item for item in operations if not _is_list(item.operation)]
    lists = [item for item in operations if _is_list(item.operation)]
    if len(gets) > 1 or len(lists) > 1:
        raise AmbiguousModule(
            f"{name} : {len(gets)} lecture(s) unitaire(s) et {len(lists)} liste(s), "
            "un module d'information n'en porte qu'une de chaque"
        )
    get = gets[0] if gets else None
    listing = lists[0] if lists else None

    options: dict[str, dict[str, Any]] = {}
    docs: dict[str, str] = {}
    limits: list[str] = []
    for item in (get, listing):
        if item is not None:
            _collect_options(item, plan.overrides, options, docs, limits, required_allowed=False)

    selector: str | None = None
    if get is not None and listing is None:
        # Sans liste, rien ne bascule : la lecture unitaire est inconditionnelle
        # et ses identifiants de chemin sont tous obligatoires. C'est le cas de
        # `get-organization` (aucun identifiant), des huit `get-dbaas-settings-*`
        # et de `get-load-balancer-service` (deux identifiants). Exiger un
        # sélecteur unique écartait ces lectures que le runtime sait exécuter,
        # puisqu'il prend le GET dès qu'il n'y a pas de liste.
        if get.operation.id.startswith("list-"):
            # Une opération nommée `list-*` dont la réponse n'est pas vue comme
            # une liste est une forme de réponse que le parser ne connaît pas,
            # pas une lecture unitaire : la rendre sous un nom singulier
            # ferait passer une liste pour un objet, en silence.
            raise AmbiguousModule(
                f"{name} : {get.operation.id} n'est pas vue comme une liste par le "
                "parser, une forme de réponse reste à mesurer"
            )
        get_override = plan.overrides.get(get.operation.key)
        for path_option in sorted(
            _resolved_option(p, get_override)
            for p in get.operation.parameters
            if _is_selector_candidate(p)
        ):
            if path_option in options:
                options[path_option]["required"] = True
    elif get is not None and listing is not None:
        get_override = plan.overrides.get(get.operation.key)
        get_paths = {
            _resolved_option(p, get_override)
            for p in get.operation.parameters
            if _is_selector_candidate(p)
        }
        list_paths = {
            _resolved_option(p, plan.overrides.get(listing.operation.key))
            for p in listing.operation.parameters
            if _is_selector_candidate(p)
        }
        candidates = sorted(get_paths - list_paths)
        if len(candidates) != 1:
            raise AmbiguousModule(
                f"{name} : {len(candidates)} sélecteur(s) possible(s) {candidates}, "
                "il en faut exactement un"
            )
        selector = candidates[0]
        # Le sélecteur bascule sur le GET ; il n'est donc jamais obligatoire.
        # Les autres identifiants de chemin, eux, le sont pour les deux
        # opérations : `id` du gadget dans `/gadget/{id}/gizmo/{gizmo-id}`.
        options[selector].pop("required", None)
        for other in sorted((get_paths | list_paths) - {selector}):
            options[other]["required"] = True

    primary = get if get is not None else listing
    if primary is None:
        raise AmbiguousModule(f"{name} : aucune opération de lecture")
    # `reveal-*` rend un secret par construction. `generate-*` aussi, mesuré :
    # `generate-sks-cluster-kubeconfig` rend des identifiants signés par le
    # cluster, `generate-data-key` du matériel de clé.
    sensitive = any(
        item.operation.id.startswith(SENSITIVE_READ_PREFIXES) for item in (get, listing) if item
    )
    return AnsibleModuleSpec(
        name=name,
        kind=OperationKind.INFO,
        product=plan.service.name,
        resource=primary.resource,
        collection=collection,
        options=options,
        option_docs=docs,
        get_operation=(
            _binding(get.operation, plan.overrides.get(get.operation.key))
            if get is not None
            else None
        ),
        list_operation=(
            _binding(listing.operation, plan.overrides.get(listing.operation.key))
            if listing is not None
            else None
        ),
        selector=selector,
        limits=tuple(sorted(set(limits))),
        sensitive_return=sensitive,
        summary=primary.operation.summary,
    )


def _build_action_spec(
    name: str,
    operations: tuple[OperationPlan, ...],
    plan: ProductPlan,
    collection: Collection,
) -> AnsibleModuleSpec:
    """Un module d'action regroupe les opérations ponctuelles d'une ressource."""
    resource = operations[0].resource
    options: dict[str, dict[str, Any]] = {}
    docs: dict[str, str] = {}
    limits: list[str] = []
    actions: list[ActionBinding] = []
    seen: dict[str, str] = {}

    # Le sélecteur est le paramètre de chemin que **toutes** les actions
    # partagent. Un paramètre de chemin propre à une action (`{field}` de
    # `reset-instance-field`) n'est pas un sélecteur : c'est une option que le
    # contrat exige pour cette action seule.
    per_operation = [
        {
            _resolved_option(p, plan.overrides.get(item.operation.key))
            for p in item.operation.parameters
            if _is_selector_candidate(p)
        }
        for item in operations
    ]
    shared = set.intersection(*per_operation) if per_operation else set()
    # Tout identifiant de chemin commun à toutes les actions est obligatoire.
    # Il y en a un le plus souvent (`{id}`), deux pour une ressource imbriquée
    # (`/sks-cluster/{id}/nodepool/{sks-nodepool-id}:scale`, sept
    # `reset-dbaas-*-user-password`), zéro pour un singleton
    # (`/iam-organization-policy:reset`). Exiger exactement un sélecteur
    # écartait neuf modules d'action que le runtime sait exécuter, puisqu'il ne
    # lit pas le sélecteur : il envoie chaque option sous le nom du contrat. Un
    # identifiant que toutes ne partagent pas reste une option propre à
    # l'action qui le porte, exigée par `required_if`.
    if not shared and any(per_operation):
        # Aucun identifiant commun alors que des actions en portent : ce sont
        # deux noms pour un même sélecteur (`{gadget-id}` chez l'une, `{id}`
        # chez les autres), et seul un override sait le dire. Zéro identifiant
        # partagé n'est légitime que si aucune action n'en porte.
        raise AmbiguousModule(
            f"{name} : les actions ne partagent aucun identifiant de chemin alors que "
            f"certaines en portent {sorted(set.union(*per_operation))} ; un override "
            "`option` doit unifier le sélecteur"
        )
    shared_ids = tuple(sorted(shared))
    selector = shared_ids[0] if len(shared_ids) == 1 else None

    for item in sorted(operations, key=lambda entry: entry.operation.id):
        action = action_name(item.operation.id, resource)
        if action in seen:
            raise AmbiguousModule(
                f"{name} : {item.operation.id} et {seen[action]} donnent la même action {action!r}"
            )
        seen[action] = item.operation.id
        override = plan.overrides.get(item.operation.key)
        required = _collect_options(
            item, plan.overrides, options, docs, limits, required_allowed=False
        )
        required.extend(
            _resolved_option(p, override)
            for p in item.operation.parameters
            if p.location is ParameterLocation.PATH
            and _resolved_option(p, override) not in shared_ids
        )
        expected = None
        always = False
        if override is not None and override.wait is not None:
            expected = override.wait.states.get(action)
            always = action in override.wait.always
        actions.append(
            ActionBinding(
                name=action,
                operation=_binding(item.operation, override),
                required=tuple(sorted({option for option in required if option not in shared_ids})),
                expected_state=expected,
                always_acts=always,
            )
        )

    for shared_id in shared_ids:
        if shared_id in options:
            options[shared_id]["required"] = True
    options = {
        "action": {"type": "str", "required": True, "choices": [a.name for a in actions]},
        **options,
    }
    docs["action"] = "The action to trigger on the " + resource.replace("_", " ") + "."

    state_fields = {
        plan.overrides.get(item.operation.key).wait.field  # type: ignore[union-attr]
        for item in operations
        if plan.overrides.get(item.operation.key) is not None
        and plan.overrides.get(item.operation.key).wait is not None  # type: ignore[union-attr]
    }
    state_field = next(iter(sorted(state_fields)), None)
    read_operation = (
        _read_binding(plan, resource, options, limits) if state_field is not None else None
    )
    return AnsibleModuleSpec(
        name=name,
        kind=OperationKind.ACTION,
        product=plan.service.name,
        resource=resource,
        collection=collection,
        options=options,
        option_docs=docs,
        selector=selector,
        actions=tuple(actions),
        state_field=state_field,
        read_operation=read_operation,
        limits=tuple(sorted(set(limits))),
    )


def _read_binding(
    plan: ProductPlan, resource: str, options: dict[str, dict[str, Any]], limits: list[str]
) -> OperationBinding | None:
    """La lecture unitaire de la ressource, pour vérifier son état après une action.

    `operation.state == success` dit que le travail est fini, pas que la
    ressource est dans l'état visé : il faut la relire. La lecture est celle du
    module d'information de la même ressource, et ses identifiants de chemin
    doivent être des options du module d'action, sinon le runtime ne saurait
    pas l'appeler. Ce qui manque est dit dans les limites, jamais deviné.
    """
    candidates = [
        item
        for item in plan.operations
        if item.resource == resource
        and item.kind is OperationKind.INFO
        and not _is_list(item.operation)
        and item.operation.http_method is HTTPMethod.GET
    ]
    if len(candidates) != 1:
        limits.append(
            f"{resource} : {len(candidates)} lecture(s) unitaire(s), l'état attendu ne "
            "sera pas vérifié après une action"
        )
        return None
    item = candidates[0]
    binding = _binding(item.operation, plan.overrides.get(item.operation.key))
    missing = sorted(set(binding.path_params) - set(options))
    if missing:
        limits.append(
            f"{item.operation.id} : la lecture demande {missing}, que le module d'action "
            "ne porte pas ; l'état attendu ne sera pas vérifié"
        )
        return None
    return binding


def action_name(operation_id: str, resource: str) -> str:
    """Le nom d'une action : les mots de l'`operationId` sans ceux de la ressource.

    >>> action_name("resize-instance-disk", "instance")
    'resize_disk'
    >>> action_name("attach-instance-to-private-network", "instance")
    'attach_to_private_network'
    >>> action_name("reset-instance-pool-field", "instance_pool")
    'reset_field'
    """
    words = split_words(operation_id)
    resource_words = resource.split("_")
    size = len(resource_words)
    for start in range(len(words) - size + 1):
        if words[start : start + size] == resource_words:
            words = words[:start] + words[start + size :]
            break
    else:
        # La ressource peut être écrite au pluriel dans l'identifiant.
        singular = [word.rstrip("s") for word in words]
        for start in range(len(words) - size + 1):
            if singular[start : start + size] == [w.rstrip("s") for w in resource_words]:
                words = words[:start] + words[start + size :]
                break
    return "_".join(words) or operation_id.replace("-", "_")


def _resolved_option(parameter: ApiParameter, override: OperationOverride | None) -> str:
    """Le nom d'option d'un paramètre : celui de l'override s'il en impose un."""
    if override is not None:
        parameter_override = override.parameters.get(parameter.name)
        if parameter_override is not None and parameter_override.option:
            return parameter_override.option
    return option_name(parameter)


def _collect_options(
    item: OperationPlan,
    overrides: OverrideSet,
    options: dict[str, dict[str, Any]],
    docs: dict[str, str],
    limits: list[str],
    *,
    required_allowed: bool,
) -> list[str]:
    """Ajoute les options d'une opération, et rend celles que le contrat exige."""
    override = overrides.get(item.operation.key)
    required: list[str] = []
    for parameter in item.operation.parameters:
        name = _resolved_option(parameter, override)
        if name in COMMON_PARAMETERS:
            continue
        if parameter.read_only:
            limits.append(f"{item.operation.id}.{parameter.name} : propriété readOnly, non exposée")
            continue
        parameter_override = override.parameters.get(parameter.name) if override else None
        if parameter_override is not None and parameter_override.expose is False:
            continue
        parameter = _apply_parameter_override(parameter, parameter_override)
        if parameter.type is ApiType.UNKNOWN:
            raise UntypedParameter(
                f"{item.operation.id}.{parameter.name} : type absent du contrat, "
                "un override `type` avec sa raison est nécessaire"
            )
        try:
            entry = argument_spec_entry(parameter)
        except UnmappedType as error:
            raise UntypedParameter(str(error)) from error
        if parameter.type is ApiType.ARRAY and parameter.item_type is None:
            limits.append(
                f"{item.operation.id}.{parameter.name} : tableau sans `items`, "
                "éléments rendus en str"
            )
        if entry.pop("required", False):
            required.append(name)
            if required_allowed:
                entry["required"] = True
        previous = options.get(name)
        if previous is not None and previous.get("type") != entry["type"]:
            raise ConflictingOption(
                f"{name} : {previous['type']} pour une opération, {entry['type']} pour une autre"
            )
        if previous is None:
            options[name] = entry
            docs[name] = parameter.description or UNDOCUMENTED
    return required


def _apply_parameter_override(
    parameter: ApiParameter, override: ParameterOverride | None
) -> ApiParameter:
    """Applique ce qu'un humain a décidé d'un paramètre : type, obligation, choix."""
    if override is None:
        return parameter
    changes: dict[str, Any] = {}
    if override.type is not None:
        changes["type"] = override.type
    if override.required is not None:
        changes["required"] = override.required
    if override.choices:
        changes["enum_values"] = tuple(override.choices)
        changes["type"] = ApiType.ENUM
    if not changes:
        return parameter
    return replace(parameter, **changes)


def _is_selector_candidate(parameter: ApiParameter) -> bool:
    """Un sélecteur est un paramètre de chemin qui **identifie** une ressource.

    Un paramètre de chemin à valeurs énumérées n'identifie rien : `{field}` de
    `/instance/{id}/{field}` vaut `labels` ou `user-data`, et c'est le nom du
    champ à remettre à zéro, donc une option de l'action. Sans cette règle,
    les quatre ressources dont la seule action est `reset-*-field` n'avaient
    aucun sélecteur commun.
    """
    return parameter.location is ParameterLocation.PATH and not parameter.enum_values


def _is_list(operation: ApiOperation) -> bool:
    return operation.response is not None and operation.response.is_list


def _binding(
    operation: ApiOperation, override: OperationOverride | None = None
) -> OperationBinding:
    def names(location: ParameterLocation) -> dict[str, str]:
        return {
            _resolved_option(p, override): p.name
            for p in operation.parameters
            if p.location is location and not p.read_only and not _hidden(p, override)
        }

    return OperationBinding(
        id=operation.id,
        method=sdk_method(operation.id),
        http_method=operation.http_method.value,
        path=operation.path,
        path_params=names(ParameterLocation.PATH),
        query_params=names(ParameterLocation.QUERY),
        body_params=names(ParameterLocation.BODY),
        payload_field=operation.response.payload_field if operation.response else None,
        is_list=_is_list(operation),
        is_async=operation.is_async,
    )


def _hidden(parameter: ApiParameter, override: OperationOverride | None) -> bool:
    """Vrai quand un override retire le paramètre des options du module."""
    if override is None:
        return False
    parameter_override = override.parameters.get(parameter.name)
    return parameter_override is not None and parameter_override.expose is False
