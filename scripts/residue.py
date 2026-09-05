"""Prouve qu'un exercice contre l'organisation réelle n'a rien laissé derrière lui.

La destruction de la plateforme ne suffit pas comme garantie, et ce n'est pas
une opinion : une construction interrompue laisse des ressources que la
destruction n'a pas listées, et un instantané survit à la suppression de son
instance, mesuré sur feint le 5 septembre 2026.

La garantie est donc un **différentiel**, et non « l'organisation doit être
vide » : le compte porte ce qu'il porte, et il doit être **inchangé**.

    python scripts/residue.py capture   avant l'exercice
    python scripts/residue.py verify    après la destruction, sort en 1 s'il reste quelque chose

L'inventaire passe par le SDK, avec les identifiants et l'endpoint de
l'environnement, sur la zone de l'exercice. **Un appel qui échoue est une
erreur, jamais un zéro** : une liste qui ne répond pas ne prouve pas qu'il ne
reste rien, elle prouve qu'on ne sait pas.

Le fichier de référence vit sous `build/`, jamais dans le dépôt : c'est l'état
d'un compte à un instant, pas un artefact du produit.
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from exoscale.api.exceptions import ExoscaleAPIException
from exoscale.api.v2 import Client

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "build" / "residue" / "baseline.json"

#: Ce qu'on inventorie, et comment : le type, la méthode du SDK qui le liste,
#: et le champ d'enveloppe. Chaque entrée est un type que la plateforme peut
#: créer, directement ou par effet de bord (le pool crée des instances,
#: l'instantané survit à l'instance).
SURFACE: tuple[tuple[str, str, str], ...] = (
    ("instance", "list_instances", "instances"),
    ("instance-pool", "list_instance_pools", "instance-pools"),
    ("load-balancer", "list_load_balancers", "load-balancers"),
    ("elastic-ip", "list_elastic_ips", "elastic-ips"),
    ("private-network", "list_private_networks", "private-networks"),
    ("security-group", "list_security_groups", "security-groups"),
    ("anti-affinity-group", "list_anti_affinity_groups", "anti-affinity-groups"),
    ("ssh-key", "list_ssh_keys", "ssh-keys"),
    ("snapshot", "list_snapshots", "snapshots"),
    ("block-storage-volume", "list_block_storage_volumes", "block-storage-volumes"),
    ("block-storage-snapshot", "list_block_storage_snapshots", "block-storage-snapshots"),
)


class ResidueError(RuntimeError):
    """L'inventaire n'a pas pu être pris, ou il reste quelque chose."""


def client_from_env() -> Client:
    cle = os.environ.get("EXOSCALE_API_KEY")
    secret = os.environ.get("EXOSCALE_API_SECRET")
    if not cle or not secret:
        raise ResidueError("EXOSCALE_API_KEY et EXOSCALE_API_SECRET sont requis")
    url = os.environ.get("EXOSCALE_API_URL") or os.environ.get("EXOSCALE_API_ENDPOINT")
    if url:
        return Client(cle, secret, url=url)
    zone = os.environ.get("EXOSCALE_ZONE")
    if not zone:
        raise ResidueError("EXOSCALE_ZONE est requis sans URL d'API")
    return Client(cle, secret, zone=zone)


def lister(client: Client, methode: str, enveloppe: str) -> list[dict[str, Any]]:
    """Liste un type de ressource. Un appel qui échoue est une erreur."""
    appel: Callable[[], Any] = getattr(client, methode)
    try:
        reponse = appel()
    except ExoscaleAPIException as erreur:
        raise ResidueError(f"`{methode}` a échoué : {erreur}") from erreur
    items = reponse.get(enveloppe) if isinstance(reponse, dict) else None
    if not isinstance(items, list):
        raise ResidueError(f"`{methode}` n'a pas rendu de liste `{enveloppe}`")
    return items


def libelle(item: dict[str, Any]) -> str:
    return str(item.get("name") or item.get("ip") or "sans nom")


def inventaire(client: Client) -> dict[str, dict[str, str]]:
    """L'état de l'organisation : par type, les identifiants présents et leur nom."""
    etat: dict[str, dict[str, str]] = {}
    for nom, methode, enveloppe in SURFACE:
        etat[nom] = {
            str(item.get("id") or item.get("name")): libelle(item)
            for item in lister(client, methode, enveloppe)
            if item.get("id") or item.get("name")
        }
    return etat


def ecarts(
    avant: dict[str, dict[str, str]], apres: dict[str, dict[str, str]]
) -> tuple[list[str], list[str]]:
    """Ce qui est apparu, et ce qui a disparu. Pure, donc testable."""
    apparus = [
        f"  {nom}  {libelle}  ({identifiant})"
        for nom, items in sorted(apres.items())
        for identifiant, libelle in sorted(items.items())
        if identifiant not in avant.get(nom, {})
    ]
    disparus = [
        f"  {nom}  {libelle}  ({identifiant})"
        for nom, items in sorted(avant.items())
        for identifiant, libelle in sorted(items.items())
        if identifiant not in apres.get(nom, {})
    ]
    return apparus, disparus


def capture() -> int:
    etat = inventaire(client_from_env())
    BASELINE.parent.mkdir(parents=True, exist_ok=True)
    BASELINE.write_text(json.dumps(etat, ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(len(v) for v in etat.values())
    print(f"référence prise : {total} ressource(s) préexistante(s), {BASELINE.relative_to(ROOT)}")
    for nom, items in sorted(etat.items()):
        if items:
            print(f"  {nom} : {', '.join(sorted(items.values()))}")
    return 0


def verify() -> int:
    if not BASELINE.is_file():
        raise ResidueError(
            f"{BASELINE.relative_to(ROOT)} est absent : lancer `capture` **avant** "
            "l'exercice. Sans référence, on ne peut rien prouver, et surtout pas "
            "l'absence de quelque chose."
        )
    avant = json.loads(BASELINE.read_text(encoding="utf-8"))
    apres = inventaire(client_from_env())
    apparus, disparus = ecarts(avant, apres)

    if apparus:
        print(f"{len(apparus)} ressource(s) apparue(s) et non détruite(s) :", file=sys.stderr)
        print("\n".join(apparus), file=sys.stderr)
        print(
            "\nL'organisation n'est pas revenue à son état d'avant. Les supprimer à la main, "
            "puis comprendre pourquoi la destruction ne les a pas emportées : c'est "
            "cette raison-là qui doit être corrigée, pas seulement la ressource.",
            file=sys.stderr,
        )
        return 1
    if disparus:
        print(f"{len(disparus)} ressource(s) préexistante(s) ont disparu :", file=sys.stderr)
        print("\n".join(disparus), file=sys.stderr)
        print(
            "\nL'exercice a détruit ce qu'il n'avait pas créé. C'est plus grave qu'un résidu.",
            file=sys.stderr,
        )
        return 1

    total = sum(len(v) for v in apres.values())
    print(f"aucun résidu : l'organisation est revenue à ses {total} ressource(s) d'avant")
    return 0


def main(argv: list[str]) -> int:
    action = argv[1] if len(argv) > 1 else ""
    if action == "capture":
        return capture()
    if action == "verify":
        return verify()
    print("usage : python scripts/residue.py capture|verify", file=sys.stderr)
    return 2


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv))
    except ResidueError as erreur:
        print(f"erreur : {erreur}", file=sys.stderr)
        raise SystemExit(1) from erreur
