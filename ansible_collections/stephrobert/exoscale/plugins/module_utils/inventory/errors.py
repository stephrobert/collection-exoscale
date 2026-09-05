# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Stéphane Robert
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""La taxonomie des échecs de découverte.

Un jeton refusé, une zone qui ne sert pas le produit et une panne d'API
n'ont pas la même gravité, et un inventaire qui les confond rend un parc
incomplet, silencieux, avec un code de retour 0 :

* **l'authentification** est fatale partout. Aucun provider ne peut travailler,
  et continuer ne produirait qu'un inventaire vide qui se présente comme
  complet ;
* **le droit refusé** est tolérable : un jeton peut légitimement n'avoir accès
  qu'à une partie du parc. C'est un avertissement, et il doit être visible ;
* **le produit absent d'une zone** n'est pas une erreur du tout, et le dire à
  chaque exécution serait du bruit permanent.

**Ce qu'Exoscale fait autrement.** Le SDK lève `ExoscaleAPIAuthException`
pour un **403**, et c'est lui qui dit « authentification » : un 403 sans cette
classe est un droit manquant sur une ressource. Le statut seul ne suffit donc
pas, et la classe de l'exception est la première chose lue.
"""

from __future__ import annotations


class InventoryError(Exception):
    """Un échec de découverte, classé."""


class AuthenticationFailed(InventoryError):
    """Les identifiants sont refusés : rien ne peut être découvert."""


class PermissionDenied(InventoryError):
    """Le jeton n'a pas le droit sur cette ressource, mais en a d'autres."""


class ProductUnavailable(InventoryError):
    """Le produit n'existe pas à cet endroit. Ce n'est pas une panne."""


class DiscoveryFailed(InventoryError):
    """L'API a échoué pour une raison qui n'est ni un droit ni une absence."""


def status_of(error: BaseException) -> int | None:
    """Le statut HTTP porté par une exception du SDK, s'il y en a un.

    `ExoscaleAPIException.response` est la réponse `requests` quand le SDK
    l'a reçue ; lu par `getattr` parce qu'une exception d'une autre origine
    (réseau, JSON) n'en porte pas.
    """
    response = getattr(error, "response", None)
    status = getattr(response, "status_code", None)
    return int(status) if isinstance(status, int) else None


def classify(error: BaseException) -> type[InventoryError]:
    """Range un échec d'API dans la bonne catégorie.

    La classe de l'exception d'abord, parce que c'est ce que le SDK sait de
    mieux : `ExoscaleAPIAuthException` est un refus d'authentification, quel
    que soit le statut. Ensuite le statut HTTP, qui est ce que l'API dit
    d'elle-même. Le texte du message n'est jamais lu : un message change sans
    prévenir.
    """
    if type(error).__name__ == "ExoscaleAPIAuthException":
        return AuthenticationFailed
    status = status_of(error)
    if status == 401:
        return AuthenticationFailed
    if status == 403:
        return PermissionDenied
    if status in (404, 501):
        return ProductUnavailable
    return DiscoveryFailed
