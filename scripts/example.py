"""Bâtit la plateforme d'exemple, l'exploite avec la collection, puis la détruit.

Deux cibles, une seule plateforme et un seul playbook :

    emulateur     feint en `--vm off`. Le plan de contrôle seul : rapide,
                  gratuit, hors ligne. C'est la cible de la CI et du poste.
    reel          l'organisation Exoscale réelle. Même plateforme, même
                  playbook, et un contrôle de résidu qui encadre l'exécution.

**La cible réelle ne se lance pas sans l'accord du mainteneur, demandé à
chaque fois.** Elle coûte de l'argent, et une ressource qui survit à un run
raté est un résidu payant. Le drapeau `--compte-reel-accorde` est la trace de
cet accord dans la commande, et son absence est un refus.

**La destruction est dans un `finally`.** Elle a lieu quand la construction
échoue, quand le playbook échoue, et quand l'utilisateur interrompt. C'est la
seule forme qui tienne la promesse « aucune ressource ne subsiste ».

    python scripts/example.py emulateur
    python scripts/example.py reel --compte-reel-accorde

`--garder` laisse la plateforme debout pour l'inspecter, contre l'émulateur
seulement.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from generator.ansible.collection import load_collection

ROOT = Path(__file__).resolve().parents[1]
STACK = ROOT / "examples" / "stack" / "platform.py"
PLAYBOOKS = ROOT / "examples" / "playbooks"
RAPPELS = ROOT / "examples" / "callback_plugins"
TRAVAIL = ROOT / "build" / "example"
CLE = TRAVAIL / "cle"

#: Préfixe des modules de la collection, pour les distinguer d'`ansible.builtin`.
PREFIXE_COLLECTION = f"{load_collection().fqcn}."

#: Ce que feint répond sur une route qu'il décline : un 404 avec ce message
#: (`resource not found` pour le mot de passe d'instance). Une tâche qui a reçu
#: ça a bien appelé le module, mais l'API n'a rien fait.
NON_SERVI = re.compile(r"does not serve|resource not found")

#: L'adresse de l'émulateur de **cet exercice**. Ni 4599, le port par défaut
#: de feint, qu'un poste où feint est développé occupe déjà ; ni 4877, celui
#: de collection-scaleway. Un exercice qui s'installe sur l'émulateur d'un
#: autre y bâtit puis détruit : ce n'est pas une gêne, c'est une destruction
#: de travail en cours. `FEINT_ADDR` reste honoré pour viser un émulateur
#: précis.
ADRESSE = os.environ.get("FEINT_ADDR", "127.0.0.1:4993")
ENDPOINT = f"http://{ADRESSE}"

CIBLES: dict[str, dict[str, Any]] = {
    "emulateur": {"emulateur": True},
    "reel": {"emulateur": False},
}


class ExempleError(RuntimeError):
    """L'exercice ne peut pas être joué, et il faut le dire au lieu de sauter."""


def lancer(
    commande: list[str],
    *,
    env: dict[str, str] | None = None,
    capture: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(commande, env=env, text=True, check=False, capture_output=capture)


def binaire(nom: str) -> str:
    chemin = shutil.which(nom)
    if not chemin:
        raise ExempleError(
            f"{nom} est introuvable. Cet exercice échoue plutôt que de se sauter : "
            "un exemple qui se saute tout seul finit par ne plus jamais tourner."
        )
    return chemin


def cle_ssh() -> str:
    """La clé de l'exercice, créée une fois et gardée sous `build/`."""
    TRAVAIL.mkdir(parents=True, exist_ok=True)
    if not CLE.exists():
        lancer(
            [
                binaire("ssh-keygen"),
                "-q",
                "-t",
                "ed25519",
                "-N",
                "",
                "-C",
                "exemple-collection-exoscale",
                "-f",
                str(CLE),
            ]
        )
    return (CLE.with_suffix(".pub")).read_text(encoding="utf-8").strip()


def refuser_emulateur_habite(env: dict[str, str]) -> None:
    """Refuse d'adopter un émulateur qui contient déjà des instances.

    Cet exercice bâtit puis **détruit**. Adopter l'émulateur de quelqu'un
    d'autre reviendrait à détruire son travail en cours, et feint est développé
    sur la même machine que ce dépôt.
    """
    from exoscale.api.v2 import Client

    try:
        client = Client(
            env["EXOSCALE_API_KEY"], env["EXOSCALE_API_SECRET"], url=env["EXOSCALE_API_ENDPOINT"]
        )
        total = len(client.list_instances().get("instances") or ())
    except Exception as erreur:
        raise ExempleError(
            f"un émulateur écoute sur {ADRESSE} mais ne répond pas à une lecture "
            f"simple ({erreur}). L'exercice refuse de l'adopter : il détruit ce "
            "qu'il a créé, et il ne sait pas ce qu'il détruirait."
        ) from erreur
    if total:
        raise ExempleError(
            f"un émulateur écoute sur {ADRESSE} et contient déjà {total} "
            "instance(s). L'exercice refuse de l'adopter : il termine par une "
            "destruction, et celle-ci emporterait ce qui s'y trouve.\n"
            "Choisir une autre adresse avec FEINT_ADDR, ou arrêter cet émulateur."
        )


def environnement_emulateur() -> dict[str, str]:
    """Les identifiants que l'émulateur accepte, dits par lui et non inventés."""
    resultat = lancer([binaire("feint"), "env", "exoscale", "--endpoint", ENDPOINT], capture=True)
    if resultat.returncode != 0:
        raise ExempleError(f"`feint env exoscale` a échoué :\n{resultat.stderr}")
    valeurs: dict[str, str] = {}
    for ligne in resultat.stdout.splitlines():
        if ligne.startswith("export "):
            nom, _, valeur = ligne.removeprefix("export ").partition("=")
            valeurs[nom.strip()] = valeur.strip().strip("'\"")
    attendu = f"{ENDPOINT}/v2"
    if valeurs.get("EXOSCALE_API_ENDPOINT") != attendu:
        raise ExempleError(
            f"`feint env` n'a pas donné EXOSCALE_API_ENDPOINT={attendu}. L'exercice s'arrête : "
            "sans cette variable, la plateforme et les playbooks parleraient à l'API réelle."
        )
    return valeurs


def plateforme(action: str, env: dict[str, str], run_id: str, sorties: Path | None = None) -> None:
    commande = [sys.executable, str(STACK), action, "--run-id", run_id]
    if action == "apply":
        commande += ["--ssh-public-key", cle_ssh(), "--output", str(sorties)]
    resultat = lancer(commande, env=env, capture=True)
    print(resultat.stderr.strip(), file=sys.stderr) if resultat.stderr.strip() else None
    if resultat.returncode != 0:
        raise ExempleError(f"`platform.py {action}` a échoué :\n{resultat.stdout[-2000:]}")
    if action == "destroy":
        print(resultat.stdout.strip())


def inventaire(env: dict[str, str]) -> dict[str, Any]:
    """Le graphe que le plugin construit sur la plateforme bâtie."""
    binaire_ansible = str(Path(sys.executable).parent / "ansible-inventory")
    resultat = lancer(
        [binaire_ansible, "-i", str(PLAYBOOKS / "inventaire.exoscale.yml"), "--list"],
        env=env,
        capture=True,
    )
    if resultat.returncode != 0:
        raise ExempleError(f"`ansible-inventory` a échoué :\n{resultat.stderr}")
    graphe = json.loads(resultat.stdout or "{}")
    if not isinstance(graphe, dict):
        raise ExempleError("`ansible-inventory` a rendu autre chose qu'un objet")
    return graphe


def _valeur(brut: Any) -> Any:
    if isinstance(brut, dict) and set(brut) == {"__ansible_unsafe"}:
        return brut["__ansible_unsafe"]
    if isinstance(brut, list):
        return [_valeur(item) for item in brut]
    return brut


def controler_inventaire(graphe: dict[str, Any], sorties: dict[str, Any]) -> None:
    """Ce que l'inventaire doit avoir trouvé, comparé à ce que la plateforme a bâti.

    C'est le contrôle qui refuse un vert obtenu sur rien : un plugin qui ne
    trouve aucune machine construit un inventaire parfaitement valide.
    """
    attendu = sorties["attendu"]
    prefixe = sorties["prefixe"]
    hostvars = {
        nom: variables
        for nom, variables in graphe.get("_meta", {}).get("hostvars", {}).items()
        if str(nom).startswith(prefixe)
    }
    if len(hostvars) != attendu["total"]:
        raise ExempleError(
            f"l'inventaire rend {len(hostvars)} machine(s) de la plateforme, "
            f"elle en a bâti {attendu['total']}"
        )
    for role in ("bastion", "web", "app"):
        groupe = [
            h
            for h in graphe.get(f"exo_label_role_{role}", {}).get("hosts", [])
            if h.startswith(prefixe)
        ]
        if len(groupe) != attendu[role]:
            raise ExempleError(
                f"le groupe exo_label_role_{role} porte {len(groupe)} machine(s), "
                f"la plateforme en a bâti {attendu[role]}"
            )

    # Le point qui distingue ce plugin : quatre machines sur cinq n'ont aucune
    # adresse publique, et doivent quand même être joignables par le bail que
    # leur réseau privé leur a donné.
    sans_prive = sorted(
        nom
        for nom, variables in hostvars.items()
        if not _valeur(variables.get("exoscale_private_ipv4"))
        and _valeur(variables.get("exoscale_manager_type")) is None
    )
    if sans_prive:
        raise ExempleError(
            f"{len(sans_prive)} machine(s) sans adresse privée découverte, dont "
            f"{sans_prive[:3]} : la jointure par les baux n'a pas eu lieu"
        )
    membres = [
        n for n, v in hostvars.items() if _valeur(v.get("exoscale_manager_type")) == "instance-pool"
    ]
    if len(membres) != attendu["pool"]:
        raise ExempleError(
            f"{len(membres)} membre(s) de pool dans l'inventaire, {attendu['pool']} attendu(s)"
        )
    print(
        f"inventaire : {len(hostvars)} machines, "
        f"{len([c for c in graphe if c.startswith('exo_')])} groupes natifs, "
        "les cinq machines de la plateforme jointes par une adresse privée, "
        "le membre du pool reconnu"
    )


def controler_plan_de_controle(env: dict[str, str], sorties: dict[str, Any]) -> None:
    """Tout ce que la plateforme déclare, vérifié auprès de l'API par le SDK.

    Un contrôle qui se sert de la collection pour juger la collection ne mesure
    plus rien : ces lectures passent par le client officiel.
    """
    from exoscale.api.v2 import Client

    url = env.get("EXOSCALE_API_URL") or env.get("EXOSCALE_API_ENDPOINT")
    client = (
        Client(env["EXOSCALE_API_KEY"], env["EXOSCALE_API_SECRET"], url=url)
        if url
        else Client(env["EXOSCALE_API_KEY"], env["EXOSCALE_API_SECRET"], zone=env["EXOSCALE_ZONE"])
    )
    prefixe = sorties["prefixe"]
    attendu = sorties["attendu"]
    constats: list[str] = []

    def exige(condition: bool, message: str) -> None:
        constats.append(("ok  " if condition else "ÉCHEC ") + message)
        if not condition:
            raise ExempleError(f"plan de contrôle : {message}")

    machines = [
        i for i in client.list_instances().get("instances") or () if i["name"].startswith(prefixe)
    ]
    exige(
        len(machines) == attendu["total"], f"{attendu['total']} machines ({len(machines)} trouvées)"
    )
    reseaux = [
        r
        for r in client.list_private_networks().get("private-networks") or ()
        if r["name"].startswith(prefixe)
    ]
    exige(len(reseaux) == 2, f"deux réseaux privés ({len(reseaux)} trouvés)")
    backend = client.get_private_network(id=sorties["ids"]["private_networks"]["backend"])
    exige(
        len(backend.get("leases") or ()) == 5,
        f"cinq baux sur backend ({len(backend.get('leases') or ())})",
    )
    groupes = [
        g
        for g in client.list_security_groups().get("security-groups") or ()
        if g["name"].startswith(prefixe)
    ]
    exige(len(groupes) == 3, f"un groupe de sécurité par étage ({len(groupes)} trouvés)")
    lb = client.get_load_balancer(id=sorties["ids"]["load_balancer"])
    exige(len(lb.get("services") or ()) == 1, "un service sur le load balancer, vers le pool")
    pool = client.get_instance_pool(id=sorties["ids"]["instance_pool"])
    exige(pool.get("size") == 1, "un pool d'une machine")
    snaps = [
        s
        for s in client.list_snapshots().get("snapshots") or ()
        if (s.get("instance") or {}).get("id") == sorties["ids"]["instances"]["worker-a"]
    ]
    exige(len(snaps) == 1, "un instantané de worker-a")
    volumes = [
        v
        for v in client.list_block_storage_volumes().get("block-storage-volumes") or ()
        if v["name"].startswith(prefixe)
    ]
    exige(len(volumes) == 1, "un volume Block Storage")
    print("plan de contrôle vérifié :")
    for constat in constats:
        print(f"  {constat}")


def artefact(journal: dict[str, Any], cible: str, run_id: str, residu: str) -> dict[str, Any]:
    """Ce que cette exécution a couvert, dérivé de ce qui s'est réellement joué.

    **Joué n'est pas appelé.** Une tâche gardée par un `when` non satisfait ne
    touche jamais l'API, et une route que feint décline répond sans rien
    faire : ni l'une ni l'autre ne compte. Un module joué une fois et sauté
    ailleurs compte comme joué : la question est « a-t-il tourné contre cette
    API », pas « toutes ses tâches ont-elles tourné ».
    """
    joues: set[str] = set()
    vus: set[str] = set()
    for tache in journal.get("taches", []):
        module = str(tache.get("module", ""))
        if not module.startswith(PREFIXE_COLLECTION):
            continue
        court = module[len(PREFIXE_COLLECTION) :]
        vus.add(court)
        if tache.get("verdict") in ("ok", "changed") and not NON_SERVI.search(
            str(tache.get("msg", ""))
        ):
            joues.add(court)
    faits = journal.get("faits", {})
    return {
        "cible": cible,
        "run_id": run_id,
        "horodatage": datetime.now(UTC).isoformat(timespec="seconds"),
        "modules_joues": sorted(joues),
        "modules_appeles_sans_reponse": sorted(vus - joues),
        "taches_jouees": len(journal.get("taches", [])),
        "routes_non_servies": sorted(faits.get("non_emules", [])),
        "idempotence_prouvee": sorted(faits.get("idempotences_prouvees", [])),
        "residu": residu,
    }


def ecrire_artefact(chemin_journal: Path, cible: str, run_id: str, residu: str) -> Path | None:
    """Écrit l'artefact à côté du journal. `None` quand rien n'a été journalisé :
    un artefact vide se lirait comme une exécution qui n'a rien couvert."""
    if not chemin_journal.is_file():
        return None
    journal = json.loads(chemin_journal.read_text(encoding="utf-8"))
    destination = TRAVAIL / f"{cible}-{run_id}.json"
    contenu = artefact(journal, cible, run_id, residu)
    destination.write_text(
        json.dumps(contenu, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8"
    )
    (TRAVAIL / f"dernier-{cible}.json").write_text(
        destination.read_text(encoding="utf-8"), encoding="utf-8"
    )
    return destination


def jouer(playbook: str, env: dict[str, str], variables: dict[str, str]) -> int:
    binaire_ansible = str(Path(sys.executable).parent / "ansible-playbook")
    commande = [
        binaire_ansible,
        "-i",
        str(PLAYBOOKS / "inventaire.exoscale.yml"),
        str(PLAYBOOKS / playbook),
    ]
    for nom, valeur in variables.items():
        commande += ["-e", f"{nom}={valeur}"]
    print(f"\n--- {playbook} ---", flush=True)
    code: int = lancer(commande, env=env).returncode
    return code


def main(argv: list[str]) -> int:
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument("cible", choices=sorted(CIBLES))
    parseur.add_argument(
        "--garder", action="store_true", help="ne pas détruire à la fin (émulateur seulement)"
    )
    parseur.add_argument(
        "--compte-reel-accorde",
        action="store_true",
        help="la trace, dans la commande, de l'accord du mainteneur pour dépenser sur son compte",
    )
    arguments = parseur.parse_args(argv[1:])
    cible = CIBLES[arguments.cible]

    if not cible["emulateur"] and not arguments.compte_reel_accorde:
        raise ExempleError(
            "la cible réelle crée des ressources facturées sur l'organisation Exoscale du "
            "mainteneur, et ne se lance pas sans son accord, demandé à chaque fois. "
            "Le drapeau --compte-reel-accorde est la trace de cet accord ; sans lui, refus."
        )
    if arguments.garder and not cible["emulateur"]:
        raise ExempleError(
            "`--garder` contre le compte réel laisse des ressources facturées debout."
        )

    run_id = f"{int(time.time()) % 100000}{secrets.token_hex(2)}"
    verdict_residu = "non vérifié"
    env = dict(os.environ)
    adopte = False

    if cible["emulateur"]:
        sonde = lancer(
            [binaire("feint"), "wait", "--addr", ADRESSE, "--timeout", "2s"], capture=True
        )
        adopte = sonde.returncode == 0
        if not adopte:
            demarrage = lancer(
                [
                    binaire("feint"),
                    "start",
                    "--addr",
                    ADRESSE,
                    "--vm",
                    "off",
                    "--cleanup",
                    "--timeout",
                    "180s",
                ],
                capture=True,
            )
            if demarrage.returncode != 0:
                raise ExempleError(f"feint n'a pas démarré :\n{demarrage.stderr}")
            print(demarrage.stdout.strip())
        env.update(environnement_emulateur())
        env.pop("EXOSCALE_API_URL", None)
        if adopte:
            refuser_emulateur_habite(env)
    else:
        print("cible : l'organisation Exoscale réelle.")

    # La référence de résidu se prend sur les deux cibles : contre l'émulateur
    # elle ne coûte rien et exerce le contrôle lui-même, qui n'a sinon aucune
    # occasion de tourner avant le jour où il compte.
    print("prise de la référence de résidu.")
    residu = [sys.executable, str(ROOT / "scripts" / "residue.py"), "capture"]
    if lancer(residu, env=env).returncode != 0:
        raise ExempleError("la référence de résidu n'a pas pu être prise")

    journal = TRAVAIL / f"journal-{run_id}.json"
    TRAVAIL.mkdir(parents=True, exist_ok=True)
    journal.unlink(missing_ok=True)
    env["ANSIBLE_CALLBACK_PLUGINS"] = str(RAPPELS)
    env["ANSIBLE_CALLBACKS_ENABLED"] = "journal"
    env["EXEMPLE_JOURNAL"] = str(journal)
    env["ANSIBLE_COLLECTIONS_PATH"] = str(ROOT)
    env["ANSIBLE_LOCALHOST_WARNING"] = "False"
    # **Une source d'inventaire qui ne se parse pas est un avertissement pour
    # Ansible, pas un échec** : `ansible-inventory --list` rend alors un graphe
    # vide et sort en 0. Mesuré ici même, au premier run : le plugin refusait
    # une option, et le lanceur lisait « 0 machine » sur un inventaire qui
    # n'avait jamais été construit. Cette variable en fait une erreur.
    env["ANSIBLE_INVENTORY_ANY_UNPARSED_IS_FAILED"] = "True"

    sorties_fichier = TRAVAIL / f"plateforme-{run_id}.json"
    code = 0
    try:
        plateforme("apply", env, run_id, sorties_fichier)
        sorties = json.loads(sorties_fichier.read_text(encoding="utf-8"))
        print(
            f"plateforme bâtie : {sorties['attendu']['total']} machines, "
            f"préfixe {sorties['prefixe']}"
        )

        controler_plan_de_controle(env, sorties)
        controler_inventaire(inventaire(env), sorties)

        extra = {"cible": arguments.cible, "prefixe": sorties["prefixe"]}
        code = jouer("modules.yml", env, extra)
        return code
    finally:
        if arguments.garder:
            print(
                "\nplateforme conservée. La détruire avec :\n"
                f"  python examples/stack/platform.py destroy --run-id {run_id}"
            )
        else:
            print("\n--- destruction ---", flush=True)
            try:
                plateforme("destroy", env, run_id)
            except ExempleError as erreur:
                print(f"LA DESTRUCTION A ÉCHOUÉ. Ne pas en rester là : {erreur}", file=sys.stderr)
                code = 1
            verifier = [sys.executable, str(ROOT / "scripts" / "residue.py"), "verify"]
            if lancer(verifier, env=env).returncode != 0:
                code = 1
                verdict_residu = "non vérifié"
            else:
                verdict_residu = "aucun" if not cible["emulateur"] else "aucun (émulateur)"
        ecrit = ecrire_artefact(journal, arguments.cible, run_id, verdict_residu)
        if ecrit is not None:
            print(f"\ncouverture de cette exécution : {ecrit.relative_to(ROOT)}")
        if cible["emulateur"] and not adopte and not arguments.garder:
            lancer([binaire("feint"), "stop", "--addr", ADRESSE], capture=True)


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv))
    except ExempleError as erreur:
        print(f"erreur : {erreur}", file=sys.stderr)
        raise SystemExit(1) from erreur
