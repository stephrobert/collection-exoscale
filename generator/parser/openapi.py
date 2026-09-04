"""Traduction d'un document OpenAPI 3.0 d'Exoscale vers l'IR canonique.

Le parser ne décide rien : il traduit. Toute décision (est-ce un module, sous
quel nom, exposé ou non) appartient au classifieur et aux overrides. Ce qu'il
ne comprend pas, il le signale dans `ApiService.warnings` plutôt que de le
laisser disparaître.

Ce que le document publié porte et ne porte pas est mesuré, pas supposé :

* **aucune pagination.** Aucune opération ne déclare `page`, `limit`, `offset`
  ni `cursor` en paramètre de requête. Le parser ne l'invente pas : il le
  signale une fois par produit dans les limites, et un module de liste rend ce
  que l'API rend, sans promettre plus ;
* **44 paramètres de chemin sans schéma** (`name`, `service-name`,
  `username`). Leur type est inconnu, et il ne se devine pas ;
* **`required` est déclaré** sur 64 corps de requête sur 142, là où Scaleway
  n'en déclare aucun. Le parser le lit, le mapping s'en sert ;
* **`readOnly` marque 169 propriétés.** Une propriété en lecture seule ne se
  déclare pas dans un `argument_spec`, et l'IR porte le drapeau ;
* **203 écritures répondent par l'objet `operation`.** L'appel est asynchrone,
  et la réponse ne dit rien de la ressource : elle dit qu'un travail a commencé.
"""

from __future__ import annotations

from typing import Any

from generator.ir.enums import ApiType, HTTPMethod, ParameterLocation
from generator.ir.models import ApiEnum, ApiOperation, ApiParameter, ApiResponse, ApiService
from generator.parser.naming import singularize_phrase, snake_case, split_words
from generator.source.base import SpecDocument

#: Méthodes HTTP qu'un document Exoscale peut porter sur un chemin.
_METHODS: dict[str, HTTPMethod] = {
    "get": HTTPMethod.GET,
    "post": HTTPMethod.POST,
    "put": HTTPMethod.PUT,
    "patch": HTTPMethod.PATCH,
    "delete": HTTPMethod.DELETE,
}

_SCALAR_TYPES: dict[str, ApiType] = {
    "string": ApiType.STRING,
    "integer": ApiType.INTEGER,
    "number": ApiType.NUMBER,
    "boolean": ApiType.BOOLEAN,
    "array": ApiType.ARRAY,
    "object": ApiType.OBJECT,
}

#: Nom du schéma que toute écriture asynchrone rend. Mesuré : 82 PUT, 62 POST
#: et 59 DELETE répondent par `#/components/schemas/operation`.
OPERATION_SCHEMA = "operation"

#: Noms sous lesquels une API pagine d'ordinaire. Aucun n'est déclaré par une
#: opération du contrat ; s'il en apparaissait un, le rapport le dirait.
_PAGINATION_NAMES: frozenset[str] = frozenset({"page", "per-page", "limit", "offset", "cursor"})


class ParseError(ValueError):
    """Le document n'a pas la forme qu'un contrat Exoscale doit avoir."""


def parse_document(spec: SpecDocument) -> ApiService:
    """Construit l'IR d'un produit à partir de son document découpé."""
    document = spec.document
    if "paths" not in document:
        raise ParseError(f"{spec.path} ne déclare aucun chemin")

    schemas: dict[str, Any] = document.get("components", {}).get("schemas", {})
    warnings: list[str] = []
    enums: dict[str, ApiEnum] = {}
    operations: list[ApiOperation] = []
    paginated: list[str] = []

    for path, path_item in document["paths"].items():
        for method_name, method in _METHODS.items():
            operation = path_item.get(method_name)
            if operation is None:
                continue
            parsed = _parse_operation(
                spec=spec,
                path=path,
                method=method,
                operation=operation,
                schemas=schemas,
                enums=enums,
                warnings=warnings,
            )
            operations.append(parsed)
            if any(
                parameter.location is ParameterLocation.QUERY
                and parameter.name in _PAGINATION_NAMES
                for parameter in parsed.parameters
            ):
                paginated.append(parsed.id)

    if operations and not paginated:
        warnings.append(
            "aucune opération ne déclare de paramètre de pagination "
            "(page, limit, offset, cursor) : une liste est rendue en une réponse, "
            "et le contrat ne promet pas qu'elle soit complète"
        )
    for identifier in paginated:
        warnings.append(
            f"{identifier} : déclare un paramètre de pagination, "
            "que ce parser ne traduit pas encore"
        )

    info = document.get("info", {})
    return ApiService(
        name=spec.product,
        version=spec.version,
        title=info.get("title"),
        description=_first_paragraph(info.get("description")),
        source=str(spec.path.name),
        zones=_zones_of(document),
        operations=tuple(sorted(operations, key=lambda op: op.id)),
        enums=tuple(sorted(enums.values(), key=lambda enum: enum.name)),
        warnings=tuple(sorted(set(warnings))),
    )


def _zones_of(document: dict[str, Any]) -> tuple[str, ...]:
    """Les zones, lues dans la variable `{zone}` de l'URL du serveur.

    Le chemin ne porte pas la zone : c'est l'hôte qui la porte
    (`https://api-{zone}.exoscale.com/v2`). Mesuré : huit zones déclarées.
    """
    for server in document.get("servers", []):
        variables = server.get("variables", {})
        zone = variables.get("zone", {})
        values = zone.get("enum")
        if values:
            return tuple(str(value) for value in values)
    return ()


def _parse_operation(
    *,
    spec: SpecDocument,
    path: str,
    method: HTTPMethod,
    operation: dict[str, Any],
    schemas: dict[str, Any],
    enums: dict[str, ApiEnum],
    warnings: list[str],
) -> ApiOperation:
    operation_id = operation.get("operationId")
    if not operation_id:
        raise ParseError(f"{method.value} {path} n'a pas d'operationId")

    parameters: list[ApiParameter] = []
    for declared in operation.get("parameters", []):
        parameters.append(
            _parse_parameter(
                declared=declared,
                schemas=schemas,
                enums=enums,
                warnings=warnings,
                operation_id=operation_id,
            )
        )
    parameters.extend(
        _parse_body(
            operation=operation,
            schemas=schemas,
            enums=enums,
            warnings=warnings,
            operation_id=operation_id,
        )
    )

    return ApiOperation(
        id=operation_id,
        product=spec.product,
        version=spec.version,
        resource=derive_resource(path, operation_id),
        http_method=method,
        path=path,
        parameters=tuple(parameters),
        response=_parse_response(operation, schemas, warnings, operation_id),
        summary=operation.get("summary") or None,
        description=_first_paragraph(operation.get("description")),
        deprecated=bool(operation.get("deprecated")),
        tags=tuple(operation.get("tags") or ()),
    )


def _parse_parameter(
    *,
    declared: dict[str, Any],
    schemas: dict[str, Any],
    enums: dict[str, ApiEnum],
    warnings: list[str],
    operation_id: str,
) -> ApiParameter:
    name = str(declared["name"])
    location = ParameterLocation(declared.get("in", "query"))
    schema = declared.get("schema")
    if schema is None:
        # Mesuré : 44 `{name}`, 43 `{service-name}` et 22 `{username}` n'ont
        # aucun schéma. Le type est inconnu, et il ne se devine pas.
        warnings.append(f"{operation_id}.{name} : paramètre de chemin sans schéma, type inconnu")
        resolved = _ResolvedType(ApiType.UNKNOWN)
        schema = {}
    else:
        resolved = _resolve_type(
            schema=schema,
            schemas=schemas,
            enums=enums,
            warnings=warnings,
            context=f"{operation_id}.{name}",
        )
    return ApiParameter(
        name=name,
        type=resolved.type,
        required=bool(declared.get("required", location is ParameterLocation.PATH)),
        location=location,
        description=_first_paragraph(declared.get("description")),
        enum_name=resolved.enum_name,
        enum_values=resolved.enum_values,
        item_type=resolved.item_type,
        default=resolved.default,
        deprecated=bool(schema.get("deprecated") or declared.get("deprecated")),
        format=schema.get("format"),
        ref=resolved.ref,
    )


def _parse_body(
    *,
    operation: dict[str, Any],
    schemas: dict[str, Any],
    enums: dict[str, ApiEnum],
    warnings: list[str],
    operation_id: str,
) -> list[ApiParameter]:
    body = operation.get("requestBody")
    if not body:
        return []
    schema = body.get("content", {}).get("application/json", {}).get("schema")
    if not schema:
        warnings.append(f"{operation_id} : corps de requête sans schéma JSON")
        return []
    schema = _deref(schema, schemas)
    properties: dict[str, Any] = schema.get("properties", {})
    if not properties:
        warnings.append(f"{operation_id} : corps de requête sans propriété déclarée")
    required = set(schema.get("required", ()))

    parameters: list[ApiParameter] = []
    for name, property_schema in properties.items():
        resolved = _resolve_type(
            schema=property_schema,
            schemas=schemas,
            enums=enums,
            warnings=warnings,
            context=f"{operation_id}.{name}",
        )
        parameters.append(
            ApiParameter(
                name=str(name),
                type=resolved.type,
                required=name in required,
                location=ParameterLocation.BODY,
                description=_first_paragraph(property_schema.get("description")),
                enum_name=resolved.enum_name,
                enum_values=resolved.enum_values,
                item_type=resolved.item_type,
                default=resolved.default,
                deprecated=bool(property_schema.get("deprecated")),
                format=property_schema.get("format"),
                ref=resolved.ref,
                read_only=bool(property_schema.get("readOnly")),
            )
        )
    return parameters


class _ResolvedType:
    """Résultat de la lecture d'un schéma de paramètre."""

    __slots__ = ("default", "enum_name", "enum_values", "item_type", "ref", "type")

    def __init__(
        self,
        type: ApiType,
        enum_name: str | None = None,
        enum_values: tuple[str, ...] = (),
        item_type: ApiType | None = None,
        default: object | None = None,
        ref: str | None = None,
    ) -> None:
        self.type = type
        self.enum_name = enum_name
        self.enum_values = enum_values
        self.item_type = item_type
        self.default = default
        self.ref = ref


def _resolve_type(
    *,
    schema: dict[str, Any],
    schemas: dict[str, Any],
    enums: dict[str, ApiEnum],
    warnings: list[str],
    context: str,
) -> _ResolvedType:
    """Traduit un schéma OpenAPI 3.0 en type de l'IR, en enregistrant les enums.

    OpenAPI 3.0 écrit un champ optionnel avec `nullable: true` (69 fois dans le
    contrat), jamais avec une liste de types ni un `oneOf` : le contrat ne
    porte aucun `oneOf`, `anyOf` ni `allOf`. S'il en portait un jour, le type
    serait inconnu et le rapport le dirait.
    """
    if not schema:
        warnings.append(f"{context} : paramètre sans schéma, type inconnu")
        return _ResolvedType(ApiType.UNKNOWN)

    for composition in ("oneOf", "anyOf", "allOf"):
        if composition in schema:
            warnings.append(f"{context} : `{composition}` non traduit, type inconnu")
            return _ResolvedType(ApiType.UNKNOWN)

    ref = schema.get("$ref")
    if ref:
        target_name = ref.rsplit("/", 1)[-1]
        target = _deref(schema, schemas)
        resolved = _resolve_type(
            schema=target, schemas=schemas, enums=enums, warnings=warnings, context=context
        )
        if resolved.type is ApiType.ENUM:
            enums.setdefault(
                target_name,
                ApiEnum(
                    name=target_name,
                    values=resolved.enum_values,
                    default=target.get("default"),
                    description=_first_paragraph(target.get("description")),
                ),
            )
            return _ResolvedType(
                ApiType.ENUM,
                enum_name=target_name,
                enum_values=resolved.enum_values,
                default=target.get("default"),
                ref=target_name,
            )
        return _ResolvedType(resolved.type, item_type=resolved.item_type, ref=target_name)

    raw_type = schema.get("type")

    if "enum" in schema:
        return _ResolvedType(
            ApiType.ENUM,
            enum_values=tuple(str(value) for value in schema["enum"]),
            default=schema.get("default"),
        )

    if raw_type == "object":
        if schema.get("additionalProperties"):
            return _ResolvedType(ApiType.MAP, default=schema.get("default"))
        return _ResolvedType(ApiType.OBJECT, default=schema.get("default"))

    if raw_type == "array":
        items = schema.get("items")
        if not items:
            warnings.append(f"{context} : tableau sans `items`, type des éléments inconnu")
            return _ResolvedType(ApiType.ARRAY, item_type=None)
        resolved_item = _resolve_type(
            schema=items,
            schemas=schemas,
            enums=enums,
            warnings=warnings,
            context=f"{context}[]",
        )
        return _ResolvedType(ApiType.ARRAY, item_type=resolved_item.type)

    if raw_type in _SCALAR_TYPES:
        return _ResolvedType(_SCALAR_TYPES[raw_type], default=schema.get("default"))

    if raw_type is None and "properties" in schema:
        return _ResolvedType(ApiType.OBJECT)

    warnings.append(f"{context} : type OpenAPI non traité ({raw_type!r})")
    return _ResolvedType(ApiType.UNKNOWN)


def _named_list_envelope(schema: dict[str, Any]) -> tuple[str, str | None] | None:
    """Le champ et la ressource d'un schéma-enveloppe nommé, ou `None`.

    Une enveloppe est un objet à **une seule** propriété, qui est un tableau.
    Un schéma à plusieurs propriétés est une ressource, même s'il porte un
    tableau : `instance` porte `security-groups` et n'est pas une liste.
    """
    if schema.get("type", "object") != "object":
        return None
    properties: dict[str, Any] = schema.get("properties", {})
    if len(properties) != 1:
        return None
    ((field_name, property_schema),) = properties.items()
    if property_schema.get("type") != "array":
        return None
    items_ref = property_schema.get("items", {}).get("$ref", "")
    return str(field_name), (items_ref.rsplit("/", 1)[-1] or None)


def _parse_response(
    operation: dict[str, Any],
    schemas: dict[str, Any],
    warnings: list[str],
    operation_id: str,
) -> ApiResponse | None:
    """Décrit la réponse de succès, et le champ qui porte réellement la ressource.

    Quatre formes mesurées sur les 135 GET du contrat :

    * 81 réponses par référence : la réponse **est** la ressource, sauf quand
      la référence est `operation`, auquel cas c'est un travail asynchrone ;
    * parmi elles, 9 références vers un schéma qui n'est pas la ressource mais
      son **enveloppe nommée** (`list-kms-keys-response`,
      `dbaas-clickhouse-roles`) : un objet à une seule propriété, tableau
      d'une ressource. Elles ne sont pas dans compute, et c'est en indexant
      ai, dbaas et kms qu'elles sont apparues : sans cette forme, `list-kms-keys`
      passait pour une lecture unitaire et `kms_key_info` était refusé ;
    * 50 objets inline à une seule propriété : une enveloppe, dont la
      propriété porte la liste (`instances`) ou l'objet utile ;
    * 2 tableaux nus (`list-events`).

    Tout autre forme est indécidable, et le rapport le dit.
    """
    responses = operation.get("responses", {})
    code = next((key for key in ("200", "201", "202", "204") if key in responses), None)
    if code is None:
        warnings.append(f"{operation_id} : aucune réponse de succès déclarée")
        return None
    success = responses[code]
    schema = success.get("content", {}).get("application/json", {}).get("schema")
    if not schema:
        return ApiResponse()

    ref = schema.get("$ref")
    if ref:
        name = ref.rsplit("/", 1)[-1]
        if name == OPERATION_SCHEMA:
            return ApiResponse(schema=name, is_operation=True)
        envelope = _named_list_envelope(schemas.get(name, {}))
        if envelope is not None:
            field_name, items_schema = envelope
            return ApiResponse(
                schema=name, payload_field=field_name, payload_schema=items_schema, is_list=True
            )
        return ApiResponse(schema=name, payload_schema=name)

    if schema.get("type") == "array":
        items_ref = schema.get("items", {}).get("$ref", "")
        return ApiResponse(payload_schema=items_ref.rsplit("/", 1)[-1] or None, is_list=True)

    properties: dict[str, Any] = schema.get("properties", {})
    if len(properties) != 1:
        warnings.append(
            f"{operation_id} : réponse inline à {len(properties)} propriétés, "
            "charge utile indécidable"
        )
        return ApiResponse()
    ((field_name, property_schema),) = properties.items()
    if property_schema.get("type") == "array":
        items_ref = property_schema.get("items", {}).get("$ref", "")
        return ApiResponse(
            payload_field=str(field_name),
            payload_schema=items_ref.rsplit("/", 1)[-1] or None,
            is_list=True,
        )
    property_ref = property_schema.get("$ref", "")
    return ApiResponse(
        payload_field=str(field_name),
        payload_schema=property_ref.rsplit("/", 1)[-1] or None,
    )


def derive_resource(path: str, operation_id: str) -> str:
    """Déduit la ressource portée par un chemin, en snake_case singulier.

    La règle tient en une phrase : la ressource est le **premier et le dernier**
    segment porteur du chemin, une fois retirés les identifiants, les suffixes
    `:verbe` et le segment d'action terminal.

    Ce qui diffère de Scaleway, et pourquoi :

    * **pas de préfixe produit/version.** `/instance/{id}` commence par la
      ressource. La règle de Scaleway, qui retire deux segments, rendait
      `unknown` sur 249 chemins sur 374 ;
    * **le verbe personnalisé est un suffixe.** `/instance/{id}:start` porte
      l'action après deux-points, à la manière de Google : 34 chemins. Le
      suffixe est retiré du segment, qui redevient un identifiant ;
    * **un segment terminal qui nomme l'action n'est pas une ressource.**
      `/dbaas-postgres/{name}/maintenance/start` finit par `start`, qui est le
      verbe de `start-dbaas-pg-maintenance`. La règle : un dernier segment
      **dont le premier mot est le verbe** de l'`operationId`, ou qui commence
      l'`operationId`, est un segment d'action. « Dont le premier mot » et non
      « égal » : `/kms-key/{id}/schedule-deletion` et
      `/sks-cluster/{id}/rotate-ccm-credentials` portent un segment d'action à
      plusieurs mots, et l'égalité stricte en faisait des ressources
      (`kms_key_schedule_deletion`, `sks_cluster_rotate_ccm_credential`), donc
      des modules fantômes. Mesuré en indexant les treize autres produits :
      douze chemins, dans kms et sks.

    * `/instance/{id}:scale` -> `instance`
    * `/security-group/{id}/rules/{rule-id}` -> `security_group_rule`
    * `/instance/{id}/{field}` -> `instance`
    * `/reverse-dns/instance/{id}` -> `reverse_dns_instance`
    * `/kms-key/{id}/schedule-deletion` -> `kms_key`

    Mesuré sur le contrat entier : 165 ressources, zéro `unknown`.
    """
    words = split_words(operation_id)
    verb = words[0] if words else ""
    bearing: list[str] = []
    for raw in path.strip("/").split("/"):
        segment = raw.split(":", 1)[0]
        if not segment or segment.startswith("{"):
            continue
        bearing.append(segment)
    if len(bearing) > 1:
        last = bearing[-1]
        last_words = split_words(last)
        if (
            (last_words and last_words[0] == verb)
            or operation_id == last
            or operation_id.startswith(last + "-")
        ):
            bearing = bearing[:-1]
    if not bearing:
        return "unknown"
    parts = [bearing[0]] if len(bearing) == 1 else [bearing[0], bearing[-1]]
    return singularize_phrase(snake_case("_".join(parts)))


def _deref(node: dict[str, Any], schemas: dict[str, Any]) -> dict[str, Any]:
    """Résout une référence locale `#/components/schemas/<nom>`."""
    ref = node.get("$ref")
    if not ref:
        return node
    name = ref.rsplit("/", 1)[-1]
    target = schemas.get(name)
    if target is None:
        raise ParseError(f"référence inconnue : {ref}")
    merged = dict(target)
    for key, value in node.items():
        if key != "$ref":
            merged.setdefault(key, value)
    return merged


def _first_paragraph(text: str | None) -> str | None:
    """Garde le premier paragraphe d'une description, sans le réécrire."""
    if not text:
        return None
    paragraph = text.strip().split("\n\n", 1)[0].strip()
    return paragraph or None
