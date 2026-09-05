"""La configuration refuse ce qu'elle ne sait pas faire, et sa clé de cache
change avec tout ce qui change le résultat."""

from __future__ import annotations

from typing import Any

import pytest

from ansible_collections.stephrobert.exoscale.plugins.module_utils.inventory.config import (
    ConfigError,
    from_options,
)

PRODUITS = ("instance",)
ZONES = ("ch-gva-2", "de-fra-1")


def _options(**valeurs: Any) -> Any:
    def get_option(nom: str) -> Any:
        return valeurs.get(nom)

    return get_option


def test_les_defauts_donnent_une_configuration_complete() -> None:
    config = from_options(_options(), PRODUITS, ZONES)
    assert config.products == ("instance",)
    assert config.hostnames == ("name", "id")
    assert config.group_by == ("product", "zone", "state")
    assert config.address.priority[0] == "private_ipv4"


@pytest.mark.parametrize(
    ("option", "valeur", "attendu"),
    [
        ("products", ["mars"], "produit"),
        ("group_by", ["couleur"], "axe"),
        ("address_priority", ["ipv5"], "famille"),
        ("zones", ["fr-par-1"], "zone"),
        ("hostnames", ["nom"], "source"),
        ("labels_match", "some", "labels_match"),
        ("labels", ["env"], "dictionnaire"),
    ],
)
def test_un_nom_inconnu_est_refuse_pas_ignore(option: str, valeur: Any, attendu: str) -> None:
    """L'ignorer produirait un inventaire silencieusement différent de la demande."""
    with pytest.raises(ConfigError, match=attendu):
        from_options(_options(**{option: valeur}), PRODUITS, ZONES)


def test_les_filtres_et_exclusions_sont_lus() -> None:
    config = from_options(
        _options(
            labels={"env": "prod", "role": None},
            exclude={"states": ["stopped"], "labels": {"x": "y"}},
        ),
        PRODUITS,
        ZONES,
    )
    assert dict(config.filters.labels) == {"env": "prod", "role": ""}
    assert config.filters.exclude_states == ("stopped",)
    assert dict(config.filters.exclude_labels) == {"x": "y"}


def test_la_cle_de_cache_change_avec_le_compte_et_les_filtres() -> None:
    """Deux comptes sans profil partageaient sinon le même parc en cache."""
    config = from_options(_options(strict=True), PRODUITS, ZONES)
    a = config.cache_fingerprint(None, "EXO1")
    b = config.cache_fingerprint(None, "EXO2")
    strict = from_options(_options(strict=False), PRODUITS, ZONES).cache_fingerprint(None, "EXO1")
    assert a != b and a != strict
    assert "EXO1" not in a
