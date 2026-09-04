"""Le mapping traduit sans deviner : un type inconnu remonte, un secret se masque."""

from __future__ import annotations

import pytest

from generator.ansible.mapping import (
    UnmappedType,
    argument_spec_entry,
    is_sensitive,
    module_name,
    sdk_method,
)
from generator.ir.enums import ApiType, OperationKind, ParameterLocation
from generator.ir.models import ApiParameter


def _parameter(name: str, type: ApiType, **kwargs: object) -> ApiParameter:
    return ApiParameter(
        name=name, type=type, required=False, location=ParameterLocation.BODY, **kwargs
    )  # type: ignore[arg-type]


def test_le_nom_du_module_ne_porte_jamais_de_verbe() -> None:
    assert module_name("compute", "instance", OperationKind.INFO) == "compute_instance_info"
    assert module_name("compute", "instance", OperationKind.ACTION) == "compute_instance_action"
    assert module_name("compute", "instance", OperationKind.MANAGE) == "compute_instance"
    assert module_name("compute", "instance", OperationKind.LIFECYCLE) is None


def test_la_methode_du_sdk_se_derive_de_loperation_id() -> None:
    assert sdk_method("start-instance") == "start_instance"
    assert sdk_method("reset-instance-field") == "reset_instance_field"


def test_required_du_contrat_devient_required_de_largument_spec() -> None:
    entry = argument_spec_entry(
        ApiParameter(
            name="disk-size", type=ApiType.INTEGER, required=True, location=ParameterLocation.BODY
        )
    )
    assert entry == {"type": "int", "required": True}


def test_un_enum_devient_des_choix() -> None:
    entry = argument_spec_entry(_parameter("rescue-profile", ApiType.ENUM, enum_values=("a", "b")))
    assert entry == {"type": "str", "choices": ["a", "b"]}


def test_un_champ_sensible_recoit_no_log() -> None:
    assert is_sensitive(_parameter("password", ApiType.STRING)) is True
    assert argument_spec_entry(_parameter("api-secret", ApiType.STRING))["no_log"] is True


def test_un_identifiant_nest_jamais_le_secret_quil_designe() -> None:
    """`admin-password-encryption-ssh-key-id` contient `password` et désigne une clé.

    Le premier nom choisi ici, `ssh-key-id`, ne contenait aucun fragment
    sensible : le test passait avec ou sans la règle, et la falsification l'a
    dit. Un test qui ne mord pas sans sa garde est un commentaire.
    """
    assert is_sensitive(_parameter("admin-password-encryption-ssh-key-id", ApiType.STRING)) is False
    assert is_sensitive(_parameter("admin-password", ApiType.STRING)) is True


def test_un_type_inconnu_leve_plutot_que_de_devenir_une_chaine() -> None:
    with pytest.raises(UnmappedType):
        argument_spec_entry(_parameter("name", ApiType.UNKNOWN))
