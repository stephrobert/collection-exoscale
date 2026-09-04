"""Le parser traduit le contrat sans rien perdre ni rien inventer."""

from __future__ import annotations

from generator.ir.enums import ApiType, ParameterLocation
from generator.ir.models import ApiService
from generator.parser.openapi import derive_resource, parse_document
from generator.source.base import VendoredSpecSource

from .conftest import GADGET_SPECS


def test_toutes_les_operations_du_produit_sont_dans_lir(gadget_service: ApiService) -> None:
    assert {operation.id for operation in gadget_service.operations} == {
        "list-gadgets",
        "create-gadget",
        "get-gadget",
        "update-gadget",
        "delete-gadget",
        "start-gadget",
        "scale-gadget",
        "reset-gadget-field",
        "reveal-gadget-password",
        "revert-gadget-to-snapshot",
        "start-gadget-maintenance",
        "list-gadget-gizmos",
        "get-gadget-gizmo",
        "list-widgets",
        "get-widget",
        "reset-widget-field",
        "get-usage-report",
        "get-gadget-quota",
        "reset-gadget-quota",
        "restart-gadget-gizmo",
    }


def test_les_zones_se_lisent_dans_lurl_du_serveur(gadget_service: ApiService) -> None:
    """Le chemin ne porte pas la zone : l'hôte la porte."""
    assert gadget_service.zones == ("ch-gva-2", "de-fra-1")


def test_un_parametre_de_chemin_est_requis(gadget_service: ApiService) -> None:
    operation = gadget_service.operation("get-gadget")
    assert operation is not None
    identifiant = operation.parameter("id")
    assert identifiant is not None
    assert identifiant.required is True
    assert identifiant.location is ParameterLocation.PATH
    assert identifiant.type is ApiType.STRING
    assert identifiant.format == "uuid"


def test_un_parametre_de_chemin_sans_schema_est_signale_et_non_devine(
    gadget_service: ApiService,
) -> None:
    """Mesuré : 44 `{name}` du contrat réel n'ont aucun schéma."""
    operation = gadget_service.operation("get-widget")
    assert operation is not None
    nom = operation.parameter("name")
    assert nom is not None
    assert nom.type is ApiType.UNKNOWN
    assert any("get-widget.name" in w and "sans schéma" in w for w in gadget_service.warnings)


def test_required_du_corps_est_lu(gadget_service: ApiService) -> None:
    """Le contrat déclare `required` sur 64 corps sur 142 : le parser s'en sert."""
    operation = gadget_service.operation("scale-gadget")
    assert operation is not None
    gadget_type = operation.parameter("gadget-type")
    assert gadget_type is not None
    assert gadget_type.required is True
    assert gadget_type.location is ParameterLocation.BODY
    assert gadget_type.type is ApiType.OBJECT
    assert gadget_type.ref == "gadget-type"


def test_une_propriete_readonly_porte_son_drapeau(gadget_service: ApiService) -> None:
    operation = gadget_service.operation("update-gadget")
    assert operation is not None
    creation = operation.parameter("created-at")
    assert creation is not None
    assert creation.read_only is True


def test_un_champ_nullable_garde_son_type(gadget_service: ApiService) -> None:
    """OpenAPI 3.0 écrit l'optionnel avec `nullable: true`, pas avec une liste."""
    operation = gadget_service.operation("update-gadget")
    assert operation is not None
    nom = operation.parameter("name")
    assert nom is not None
    assert nom.type is ApiType.STRING


def test_un_enum_reference_est_enregistre_une_fois(gadget_service: ApiService) -> None:
    names = [enum.name for enum in gadget_service.enums]
    assert names == sorted(names), "les enums doivent sortir triés, pour un IR déterministe"
    assert "gadget-state" not in names, "un enum readOnly d'une réponse n'est pas un paramètre"


def test_un_enum_inline_devient_des_choix(gadget_service: ApiService) -> None:
    operation = gadget_service.operation("start-gadget")
    assert operation is not None
    profil = operation.parameter("rescue-profile")
    assert profil is not None
    assert profil.type is ApiType.ENUM
    assert profil.enum_values == ("netboot", "netboot-efi")
    assert profil.enum_name is None


def test_une_map_est_reconnue(gadget_service: ApiService) -> None:
    operation = gadget_service.operation("update-gadget")
    assert operation is not None
    labels = operation.parameter("labels")
    assert labels is not None
    assert labels.type is ApiType.MAP


def test_une_ecriture_repond_par_une_operation_asynchrone(gadget_service: ApiService) -> None:
    """203 écritures sur 374 du contrat réel : le fait est porté par l'IR."""
    start = gadget_service.operation("start-gadget")
    get = gadget_service.operation("get-gadget")
    assert start is not None and get is not None
    assert start.is_async is True
    assert start.response is not None and start.response.schema == "operation"
    assert get.is_async is False


def test_une_enveloppe_de_liste_designe_son_champ(gadget_service: ApiService) -> None:
    liste = gadget_service.operation("list-gadgets")
    assert liste is not None
    assert liste.response is not None
    assert liste.response.payload_field == "gadgets"
    assert liste.response.payload_schema == "gadget"
    assert liste.response.is_list is True


def test_une_reponse_par_reference_est_la_ressource(gadget_service: ApiService) -> None:
    unite = gadget_service.operation("get-gadget")
    assert unite is not None
    assert unite.response is not None
    assert unite.response.schema == "gadget"
    assert unite.response.payload_field is None
    assert unite.response.is_list is False


def test_une_reponse_inline_a_plusieurs_proprietes_est_signalee(
    gadget_service: ApiService,
) -> None:
    """Reproduit `get-console-proxy-url` du contrat réel : trois propriétés, pas d'enveloppe."""
    assert any("get-usage-report" in w and "3 propriétés" in w for w in gadget_service.warnings)


def test_labsence_de_pagination_est_signalee_et_non_inventee(gadget_service: ApiService) -> None:
    assert any("pagination" in w for w in gadget_service.warnings)


def test_la_description_garde_le_premier_paragraphe(gadget_service: ApiService) -> None:
    assert gadget_service.description == "Un produit de test."


def test_la_ressource_se_deduit_du_chemin() -> None:
    """Premier et dernier segment porteur, suffixe `:verbe` et segment d'action retirés."""
    assert derive_resource("/gadget", "list-gadgets") == "gadget"
    assert derive_resource("/gadget/{id}", "get-gadget") == "gadget"
    assert derive_resource("/gadget/{id}:start", "start-gadget") == "gadget"
    assert derive_resource("/gadget/{id}/{field}", "reset-gadget-field") == "gadget"
    assert derive_resource("/gadget/{id}/gizmo/{gizmo-id}", "get-gadget-gizmo") == "gadget_gizmo"
    assert derive_resource("/gadget/{id}/maintenance/start", "start-gadget-maintenance") == (
        "gadget_maintenance"
    )
    assert derive_resource("/kms-key/{id}/re-encrypt", "re-encrypt") == "kms_key"
    assert derive_resource("/security-group/{id}/rules/{rule-id}", "delete-rule") == (
        "security_group_rule"
    )


def test_la_ressource_est_stable_avec_ou_sans_identifiant(gadget_service: ApiService) -> None:
    par_operation = {operation.id: operation.resource for operation in gadget_service.operations}
    assert par_operation["list-gadgets"] == "gadget"
    assert par_operation["get-gadget"] == "gadget"
    assert par_operation["start-gadget"] == "gadget"
    assert par_operation["list-gadget-gizmos"] == "gadget_gizmo"
    assert par_operation["get-gadget-gizmo"] == "gadget_gizmo"


def test_la_cle_porte_produit_version_ressource_et_identifiant(
    gadget_service: ApiService,
) -> None:
    operation = gadget_service.operation("start-gadget")
    assert operation is not None
    assert operation.key == "gadget.v2.Gadget.start-gadget"


def test_le_parsing_est_deterministe() -> None:
    source = VendoredSpecSource(root=GADGET_SPECS)
    premier = parse_document(source.load("gadget", "v2")).to_json()
    second = parse_document(source.load("gadget", "v2")).to_json()
    assert premier == second


def test_une_enveloppe_de_liste_nommee_est_une_liste(gadget_service: ApiService) -> None:
    """Neuf `list-*` du contrat réel répondent par une référence vers un schéma
    qui n'est pas la ressource mais son enveloppe (`list-kms-keys-response`).

    Sans cette forme, `list-kms-keys` passait pour une lecture unitaire et
    `kms_key_info` était refusé comme ambigu. Le laboratoire la reproduit sur
    `list-widgets`.
    """
    operation = next(op for op in gadget_service.operations if op.id == "list-widgets")
    assert operation.response is not None
    assert operation.response.is_list
    assert operation.response.schema == "list-widgets-response"
    assert operation.response.payload_field == "widgets"
    assert operation.response.payload_schema == "widget"


def test_une_reference_vers_une_ressource_nest_pas_une_liste(gadget_service: ApiService) -> None:
    """Le cas voisin : `gadget` porte des propriétés, dont aucune n'est seule."""
    operation = next(op for op in gadget_service.operations if op.id == "get-gadget")
    assert operation.response is not None
    assert not operation.response.is_list
    assert operation.response.payload_schema == "gadget"


def test_un_segment_daction_a_plusieurs_mots_nest_pas_une_ressource() -> None:
    """`/kms-key/{id}/schedule-deletion` donnait `kms_key_schedule_deletion`.

    Douze chemins de kms et sks portent un segment d'action à plusieurs mots
    dont le premier est le verbe de l'`operationId` ; l'égalité stricte en
    faisait des ressources, donc des modules fantômes.
    """
    assert (
        derive_resource("/kms-key/{id}/schedule-deletion", "schedule-kms-key-deletion") == "kms_key"
    )
    assert (
        derive_resource("/sks-cluster/{id}/rotate-ccm-credentials", "rotate-sks-ccm-credentials")
        == "sks_cluster"
    )
    assert (
        derive_resource("/kms-key/{id}/list-key-rotations", "list-kms-key-rotations") == "kms_key"
    )


def test_un_segment_unique_nest_jamais_retire(gadget_service: ApiService) -> None:
    """Le cas voisin : `/gadget-quota` sous `get-gadget-quota` reste une ressource,
    et un segment dont le premier mot n'est pas le verbe aussi."""
    assert derive_resource("/gadget-quota", "get-gadget-quota") == "gadget_quota"
    assert derive_resource("/dbaas-postgres/{name}/migration/stop", "stop-dbaas-pg-migration") == (
        "dbaas_postgres_migration"
    )
    assert derive_resource("/reverse-dns/instance/{id}", "get-reverse-dns-instance") == (
        "reverse_dns_instance"
    )
