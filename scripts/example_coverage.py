"""Le troisième étage de couverture : ce que l'exemple exerce, et ce qu'un run a joué.

Le dépôt publie deux ratios, chacun nommé, chacun avec sa fraction :
**classées** pour génération automatique, et **portées par un module**. Ils
disent ce que le générateur autorise et ce qu'il produit. Il en manquait un
troisième, et c'est le seul qui parle d'usage : un module écrit n'est pas un
module éprouvé.

Trois choses distinctes, et les confondre serait le maquillage habituel :

* **appelé par l'exemple** se dérive hors ligne, du texte des playbooks. C'est
  une intention : le playbook nomme le module. Ce nombre entre dans le README ;
* **joué contre une cible** vient de l'artefact qu'un run laisse derrière lui,
  et il ne vaut que pour le run qui l'a produit. Une tâche sautée ou une route
  non émulée n'y comptent pas ;
* **idempotence prouvée** vient du même artefact.

    python scripts/example_coverage.py            la matrice, en texte
    python scripts/example_coverage.py --check    la porte : un module sans cible ni raison échoue
    python scripts/example_coverage.py --diff     le dernier run réel contre le dernier run feint
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import yaml

from generator.ansible.collection import load_collection
from generator.source.base import DEFAULT_SPEC_ROOT, read_products

ROOT = Path(__file__).resolve().parents[1]
PLAYBOOKS = ROOT / "examples" / "playbooks"
ARTEFACTS = ROOT / "build" / "example"


def _plugins() -> Path:
    return load_collection().path / "plugins"


#: Le répertoire des modules et celui des plugins d'inventaire, dérivés de
#: `galaxy.yml` : un test les remplace par un dépôt de laboratoire.
MODULES = _plugins() / "modules"
INVENTAIRE = _plugins() / "inventory"

#: Préfixe complet d'un contenu de cette collection dans un playbook.
PREFIXE = f"{load_collection().fqcn}."

#: Les produits entiers qu'aucune cible de la stack ne peut exercer, et
#: **pourquoi**. Mesuré le 4 septembre 2026 sur feint 0.12.1, dont le pack
#: Exoscale ne sert aucune route de ces produits ; et sur le compte réel,
#: chacun demande une ressource facturée à demeure ou hors du périmètre.
#:
#: Ce n'est pas une liste de dispenses : c'est le seul endroit où un écart a le
#: droit d'exister, et il y est nommé avec sa mesure. Le contrôle refuse un
#: produit déclaré ici dont l'exemple appelle pourtant un module.
PRODUITS_SANS_CIBLE: dict[str, str] = {
    "dbaas": (
        "feint 0.12.1 ne sert aucune des 146 opérations de DBaaS (mesuré sur "
        "/_feint/routes le 5 septembre 2026), et un service de base de données "
        "réel est facturé à l'heure dès sa création : la cible n'existe que sur le "
        "compte, et elle coûte."
    ),
    "sks": (
        "feint 0.12.1 ne sert aucune des 25 opérations de SKS, et un cluster "
        "Kubernetes réel est facturé dès sa création."
    ),
    "ai": (
        "feint 0.12.1 ne sert aucune des 22 opérations d'AI, et un déploiement "
        "réel réserve un GPU facturé."
    ),
    "iam": (
        "feint 0.12.1 ne sert aucune des 18 opérations d'IAM ; sur le compte réel, "
        "rôles et clés d'API sont à l'échelle de l'organisation, hors du périmètre "
        "d'une plateforme éphémère."
    ),
    "kms": (
        "feint 0.12.1 ne sert aucune des 16 opérations de KMS, et une clé réelle "
        "porte une suppression différée qui survit à toute destruction : le résidu "
        "zéro n'est pas tenable."
    ),
    "dns": (
        "feint 0.12.1 ne sert aucune des 10 opérations de DNS, et une zone réelle "
        "demande un domaine que la plateforme n'a pas."
    ),
    "sos": (
        "feint 0.12.1 ne sert aucune des 2 opérations de SOS, et un seau réel vit "
        "hors des zones de calcul, hors du périmètre de la plateforme."
    ),
}

#: Les modules qu'aucune cible ne peut exercer, un par un, avec leur raison.
SANS_CIBLE: dict[str, str] = {}

#: Les cibles de l'exercice, dans l'ordre où leur preuve coûte cher.
CIBLES = ("emulateur", "reel")


class CouvertureError(RuntimeError):
    """Une source manque ou se contredit, et un nombre faux serait pire."""


def non_modules() -> set[str]:
    """Ce qui porte le préfixe de la collection sans être un module : les
    plugins d'inventaire, lus sur le disque et jamais nommés ici."""
    if not INVENTAIRE.is_dir():
        return set()
    return {chemin.stem for chemin in INVENTAIRE.glob("*.py") if not chemin.stem.startswith("_")}


def modules_ecrits() -> set[str]:
    if not MODULES.is_dir():
        raise CouvertureError(f"{MODULES} n'existe pas : lancer `mise run generate`.")
    return {chemin.stem for chemin in MODULES.glob("*.py") if chemin.stem != "__init__"}


def produit_de(module: str, produits: tuple[str, ...]) -> str | None:
    """Le produit d'un module : le plus long préfixe de son nom qui est un produit."""
    for produit in sorted(produits, key=len, reverse=True):
        if module.startswith(produit + "_"):
            return produit
    return None


def produits_indexes() -> tuple[str, ...]:
    try:
        return tuple(entree.product for entree in read_products(DEFAULT_SPEC_ROOT))
    except FileNotFoundError:
        return ()


def _taches(noeud: Any) -> Iterator[dict[str, Any]]:
    """Toutes les tâches d'un document, `block`, `rescue` et `always` compris."""
    if isinstance(noeud, list):
        for element in noeud:
            yield from _taches(element)
        return
    if not isinstance(noeud, dict):
        return
    yield noeud
    for cle in ("tasks", "pre_tasks", "post_tasks", "handlers", "block", "rescue", "always"):
        if cle in noeud:
            yield from _taches(noeud[cle])


def modules_appeles() -> set[str]:
    """Ce que les playbooks appellent, lu dans les **clés de tâches**.

    **Pas dans le texte.** Un module cité dans un commentaire qui explique son
    absence suffirait sinon à franchir la porte : le contrôle mesurerait la
    prose du playbook, pas ce qu'il joue.
    """
    ecrits = modules_ecrits()
    trouves: set[str] = set()
    for chemin in sorted(PLAYBOOKS.glob("*.yml")):
        document = yaml.safe_load(chemin.read_text(encoding="utf-8"))
        for tache in _taches(document):
            for cle in tache:
                nom = str(cle)
                if nom.startswith(PREFIXE):
                    trouves.add(nom[len(PREFIXE) :])
        # Un fichier d'inventaire n'est pas un playbook : son plugin se déclare
        # par une clé `plugin`, et c'est le seul cas où un nom complet compte
        # hors d'une clé de tâche.
        if isinstance(document, dict) and str(document.get("plugin", "")).startswith(PREFIXE):
            trouves.add(str(document["plugin"])[len(PREFIXE) :])
    inconnus = sorted(trouves - ecrits - non_modules())
    if inconnus:
        raise CouvertureError(
            f"les playbooks nomment {inconnus}, qui n'est ni un module écrit ni un plugin "
            "d'inventaire. Faute de frappe, ou module supprimé sans que l'exemple suive."
        )
    return trouves & ecrits


def sans_cible(ecrits: set[str]) -> dict[str, str]:
    """Les modules déclarés sans cible, par produit entier ou un par un."""
    produits = produits_indexes()
    declares: dict[str, str] = {}
    for module in sorted(ecrits):
        produit = produit_de(module, produits)
        if produit in PRODUITS_SANS_CIBLE:
            declares[module] = PRODUITS_SANS_CIBLE[produit]
    declares.update({nom: raison for nom, raison in SANS_CIBLE.items() if nom in ecrits})
    return declares


def artefacts() -> dict[str, dict[str, Any]]:
    """Le dernier run enregistré par cible, quand il y en a un."""
    trouves: dict[str, dict[str, Any]] = {}
    for cible in CIBLES:
        chemin = ARTEFACTS / f"dernier-{cible}.json"
        if chemin.is_file():
            trouves[cible] = json.loads(chemin.read_text(encoding="utf-8"))
    return trouves


def _ratio(numerateur: int, denominateur: int) -> str:
    """Un ratio sans dénominateur est indéfini, pas nul."""
    if denominateur == 0:
        return "n/a"
    return f"{numerateur / denominateur * 100:.1f} %".replace(".", ",", 1)


def mesurer() -> dict[str, Any]:
    ecrits = modules_ecrits()
    appeles = modules_appeles()
    declares = sans_cible(ecrits)
    runs = artefacts()
    return {
        "modules_ecrits": sorted(ecrits),
        "appeles_par_lexemple": sorted(appeles),
        "jamais_appeles": sorted(ecrits - appeles),
        "sans_cible_declaree": sorted(declares),
        "declarations_perimees": sorted(set(declares) & appeles),
        "non_couverts": sorted(ecrits - appeles - set(declares)),
        "ratio_appeles": _ratio(len(appeles), len(ecrits)),
        "runs": {
            cible: {
                "horodatage": run.get("horodatage"),
                "run_id": run.get("run_id"),
                "modules_joues": sorted(run.get("modules_joues", [])),
                "ratio_joues": _ratio(len(run.get("modules_joues", [])), len(ecrits)),
                "idempotence_prouvee": len(run.get("idempotence_prouvee", [])),
                "residu": run.get("residu"),
            }
            for cible, run in runs.items()
        },
    }


def rendre(mesure: dict[str, Any]) -> str:
    ecrits = len(mesure["modules_ecrits"])
    lignes = [
        f"modules écrits : {ecrits}",
        f"appelés par l'exemple : {len(mesure['appeles_par_lexemple'])} "
        f"sur {ecrits} ({mesure['ratio_appeles']})",
        f"déclarés sans cible, avec leur raison : {len(mesure['sans_cible_declaree'])}",
        "",
        "  ce ratio dit que le playbook nomme le module, pas qu'un run l'a joué.",
        "  Les deux se distinguent, et le second ne vaut que pour le run qui l'a produit.",
        "",
    ]
    if mesure["non_couverts"]:
        lignes += [
            "ni appelés ni déclarés :",
            *(f"  {nom}" for nom in mesure["non_couverts"]),
            "",
        ]
    if not mesure["runs"]:
        lignes += [
            "aucun run enregistré sous build/example/. Le dire vaut mieux que",
            "d'écrire 0 % : rien n'a été mesuré, ce n'est pas que rien n'a marché.",
        ]
        return "\n".join(lignes) + "\n"
    lignes.append("derniers runs enregistrés :")
    for cible, run in mesure["runs"].items():
        lignes += [
            f"  {cible:10s} {run['horodatage']}  run {run['run_id']}",
            f"             joués {len(run['modules_joues'])} sur {ecrits} "
            f"({run['ratio_joues']}) · idempotences prouvées "
            f"{run['idempotence_prouvee']} · résidu : {run['residu']}",
        ]
    return "\n".join(lignes) + "\n"


def comparer(mesure: dict[str, Any]) -> dict[str, Any]:
    """Ce que le cloud réel sert et que l'émulateur ne sert pas : le matériau
    d'une issue de feint, mesuré des deux côtés avec le même playbook."""
    runs = mesure["runs"]
    reel = runs.get("reel")
    feint = runs.get("emulateur")
    if reel is None or feint is None:
        return {}
    joues_reel = set(reel["modules_joues"])
    joues_feint = set(feint["modules_joues"])
    return {
        "reel": reel,
        "feint": feint,
        "servis_par_le_reel_seul": sorted(joues_reel - joues_feint),
        "servis_par_feint_seul": sorted(joues_feint - joues_reel),
    }


def rendre_comparaison(ecart: dict[str, Any]) -> str:
    if not ecart:
        return (
            "il manque un artefact pour comparer. Lancer `mise run example` et\n"
            "`mise run example:reel` : la comparaison porte sur ce que chaque\n"
            "exécution a réellement joué, pas sur ce que le playbook nomme.\n"
        )
    reel, feint = ecart["reel"], ecart["feint"]
    lignes = [
        f"reel        {reel['horodatage']}  run {reel['run_id']}  "
        f"{len(reel['modules_joues'])} modules joués",
        f"emulateur   {feint['horodatage']}  run {feint['run_id']}  "
        f"{len(feint['modules_joues'])} modules joués",
        "",
    ]
    seuls = ecart["servis_par_le_reel_seul"]
    if seuls:
        lignes += [
            f"servis par le cloud réel et pas par feint ({len(seuls)}) :",
            *(f"  {nom}" for nom in seuls),
            "",
            "  Chacun a été appelé des deux côtés. C'est le matériau d'une issue feint.",
        ]
    else:
        lignes += ["feint sert tout ce que le cloud réel a servi."]
    if ecart["servis_par_feint_seul"]:
        lignes += [
            "",
            "servis par feint et pas par le cloud réel :",
            *(f"  {nom}" for nom in ecart["servis_par_feint_seul"]),
            "",
            "  C'est l'écart le plus intéressant : feint accepte ce que l'API refuse.",
        ]
    return "\n".join(lignes) + "\n"


def main(argv: list[str]) -> int:
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument("--json", action="store_true", help="sortir la mesure en JSON")
    parseur.add_argument(
        "--check",
        action="store_true",
        help="échouer si un module livré n'est ni appelé par un playbook ni déclaré sans cible",
    )
    parseur.add_argument(
        "--diff",
        action="store_true",
        help="comparer le dernier run réel au dernier run contre l'émulateur",
    )
    arguments = parseur.parse_args(argv[1:])
    try:
        mesure = mesurer()
    except CouvertureError as erreur:
        print(f"erreur : {erreur}", file=sys.stderr)
        return 1

    if arguments.diff:
        ecart = comparer(mesure)
        print(
            json.dumps(ecart, indent=2, ensure_ascii=False)
            if arguments.json
            else rendre_comparaison(ecart)
        )
        return 0

    if arguments.check:
        # **Hors ligne et déterministe**, donc légitime dans `mise run check` :
        # ce contrôle lit le texte des playbooks et le répertoire des modules,
        # jamais un artefact de run.
        manquants = mesure["non_couverts"]
        if manquants:
            print(
                f"{len(manquants)} module(s) livré(s) qu'aucun playbook d'exemple n'appelle,\n"
                "et qui ne sont pas déclarés sans cible :\n"
                + "\n".join(f"  {nom}" for nom in manquants)
                + "\n\nUn module écrit que rien n'exerce est un module dont on ignore s'il\n"
                "marche, et la collection en publie le nom comme si de rien n'était.\n"
                "Étendre `examples/playbooks/modules.yml`, et la plateforme si le module\n"
                "n'a pas de cible. Si aucune cible n'est possible, l'écrire dans\n"
                "`SANS_CIBLE` ou `PRODUITS_SANS_CIBLE` avec sa raison et sa mesure.",
                file=sys.stderr,
            )
            return 1

        # Une déclaration sans cible sur un module que l'exemple appelle
        # pourtant est une déclaration morte : elle raconte un obstacle qui
        # n'existe plus.
        perimees = mesure["declarations_perimees"]
        if perimees:
            print(
                f"{len(perimees)} module(s) déclarés sans cible que l'exemple appelle "
                f"pourtant : {perimees}.\nRetirer la déclaration : elle décrit un obstacle "
                "qui n'existe plus.",
                file=sys.stderr,
            )
            return 1

        exerces = len(mesure["appeles_par_lexemple"])
        total = len(mesure["modules_ecrits"])
        declares = len(mesure["sans_cible_declaree"])
        print(
            f"{exerces} module(s) sur {total} appelés par l'exemple, "
            f"{declares} déclarés sans cible avec leur raison"
        )
        return 0

    print(json.dumps(mesure, indent=2, ensure_ascii=False) if arguments.json else rendre(mesure))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
