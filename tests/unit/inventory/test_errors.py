"""La taxonomie des échecs, lue sur la classe de l'exception puis le statut."""

from __future__ import annotations

from types import SimpleNamespace

from ansible_collections.stephrobert.exoscale.plugins.module_utils.inventory.errors import (
    AuthenticationFailed,
    DiscoveryFailed,
    PermissionDenied,
    ProductUnavailable,
    classify,
)


class ExoscaleAPIAuthException(Exception):
    """Le nom que le SDK donne à un refus d'authentification : un 403."""


class ExoscaleAPIClientException(Exception):
    def __init__(self, message: str, status: int) -> None:
        super().__init__(message)
        self.response = SimpleNamespace(status_code=status)


def test_le_sdk_dit_authentification_par_la_classe_meme_en_403() -> None:
    assert classify(ExoscaleAPIAuthException("forbidden")) is AuthenticationFailed


def test_un_403_ordinaire_est_un_droit_manquant() -> None:
    assert classify(ExoscaleAPIClientException("forbidden", 403)) is PermissionDenied


def test_un_401_est_fatal() -> None:
    assert classify(ExoscaleAPIClientException("unauthorized", 401)) is AuthenticationFailed


def test_une_absence_nest_pas_une_panne() -> None:
    assert classify(ExoscaleAPIClientException("not found", 404)) is ProductUnavailable


def test_le_reste_est_une_panne() -> None:
    assert classify(ExoscaleAPIClientException("boom", 500)) is DiscoveryFailed
    assert classify(ConnectionError("réseau")) is DiscoveryFailed
