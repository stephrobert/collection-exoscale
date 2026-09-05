"""Déploie la plateforme d'exemple, l'exploite avec la collection, puis la détruit.

Deux cibles, une seule stack Terraform et un seul playbook :

    emulateur     feint en `--vm off`. Le plan de contrôle seul : rapide,
                  gratuit, hors ligne. C'est la cible de la CI et du poste.
    reel          l'organisation Exoscale réelle. Même stack, même playbook,
                  et un contrôle de résidu qui encadre l'exécution.

**La cible réelle ne se lance pas sans l'accord du mainteneur, demandé à
chaque fois.** Elle coûte de l'argent, et une ressource qui survit à un run
raté est un résidu payant. Le drapeau `--compte-reel-accorde` est la trace de
cet accord dans la commande, et son absence est un refus.

**Le fournisseur Terraform est tenu à un plancher.** Sous 0.71.0, il n'honorait
`EXOSCALE_API_ENDPOINT` que pour un de ses deux clients, et un `apply` se
scindait entre l'émulateur et un compte payant. La stack épingle 0.71.0, et ce
lanceur relit la version que `terraform init` a résolue avant d'appliquer quoi
que ce soit : une épingle se modifie, un contrôle mord.

**La destruction est dans un `finally`.** Elle a lieu quand l'application
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
STACK = ROOT / "examples" / "stack"
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

#: La zone quand rien ne la dit. Contre l'émulateur, `feint env exoscale`
#: exporte la sienne et elle prime.
ZONE_PAR_DEFAUT = "ch-gva-2"

#: Le plancher du fournisseur Terraform, et la raison est mesurée : en dessous,
#: le client v2 du fournisseur ignorait `EXOSCALE_API_ENDPOINT`, et un `apply`
#: se scindait entre l'émulateur et un compte payant (feint#525, en amont
#: exoscale/terraform-provider-exoscale#573, corrigé dans 0.71.0). La stack
#: épingle une version exacte ; ce plancher est la seconde barrière, celle qui
#: tient quand quelqu'un abaisse l'épingle.
PLANCHER_PROVIDER = (0, 71, 0)

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


def version_de(commande: list[str]) -> str:
    """La première ligne de ce qu'un outil répond à `version`, pour l'artefact."""
    resultat = lancer(commande, capture=True)
    premiere = (resultat.stdout or resultat.stderr).strip().splitlines()
    return premiere[0] if premiere else "inconnue"


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
            "sans cette variable, Terraform et les playbooks parleraient à l'API réelle."
        )
    return valeurs


# ---- Terraform ---------------------------------------------------------------


def terraform(
    action: str,
    env: dict[str, str],
    variables: dict[str, str],
    *,
    json_sortie: bool = False,
) -> subprocess.CompletedProcess[str]:
    commande = [binaire("terraform"), f"-chdir={STACK}", action, "-no-color", "-input=false"]
    if action in ("apply", "destroy"):
        commande.append("-auto-approve")
    if action == "output":
        commande = [binaire("terraform"), f"-chdir={STACK}", "output", "-json"]
    else:
        for nom, valeur in variables.items():
            commande += ["-var", f"{nom}={valeur}"]
    return lancer(commande, env=env, capture=json_sortie)


def version_lisible(version: str) -> tuple[int, ...] | None:
    """`0.71.0` en `(0, 71, 0)`, et `None` pour ce qui ne se lit pas."""
    try:
        return tuple(int(segment) for segment in version.strip().lstrip("v").split("."))
    except ValueError:
        return None


def sous_le_plancher(version: str) -> bool:
    """Vrai quand la version résolue du fournisseur ne doit pas appliquer.

    Une version illisible est **sous** le plancher : ce lanceur s'apprête à
    créer des ressources, et ce qu'il ne sait pas lire ne l'y autorise pas.
    C'est l'inverse du choix de feint, qui sert un agent qu'il ne sait pas
    lire, et les deux se justifient : lui refuse une version mesurée
    défaillante, ce lanceur n'applique que sur une version mesurée saine.
    """
    lue = version_lisible(version)
    if lue is None:
        return True
    return lue < PLANCHER_PROVIDER


def provider_resolu(env: dict[str, str]) -> str:
    """La version du fournisseur exoscale que `terraform init` a installée.

    Lue dans `terraform version -json`, dont la clé porte l'hôte du registre :
    `registry.terraform.io` pour Terraform, `registry.opentofu.org` pour
    OpenTofu. La fin de la clé suffit, et c'est ce qui laisse un jour un
    binaire remplacer l'autre.
    """
    resultat = lancer(
        [binaire("terraform"), f"-chdir={STACK}", "version", "-json"], env=env, capture=True
    )
    if resultat.returncode != 0:
        raise ExempleError(f"`terraform version -json` a échoué :\n{resultat.stderr}")
    selections = json.loads(resultat.stdout or "{}").get("provider_selections") or {}
    for source, version in selections.items():
        if str(source).endswith("/exoscale/exoscale"):
            return str(version)
    raise ExempleError(
        "aucun fournisseur exoscale résolu après `terraform init` : la stack ne le "
        "déclare plus, ou l'initialisation n'a rien installé."
    )


def exiger_le_plancher(env: dict[str, str]) -> str:
    """Refuse d'appliquer avec un fournisseur sous le plancher, et rend la version.

    La stack épingle une version exacte, et ce contrôle existe quand même :
    une épingle se modifie dans un fichier, et le jour où quelqu'un l'abaisse
    pour essayer quelque chose, c'est ici que ça s'arrête, avant le premier
    appel d'API.
    """
    version = provider_resolu(env)
    plancher = ".".join(str(segment) for segment in PLANCHER_PROVIDER)
    if sous_le_plancher(version):
        raise ExempleError(
            f"le fournisseur exoscale résolu est {version}, sous le plancher {plancher}. "
            "En dessous, un apply se scinde entre l'émulateur et un compte payant "
            "(feint#525, exoscale/terraform-provider-exoscale#573) : rien n'est appliqué. "
            "Relever la version dans examples/stack/providers.tf, puis `terraform init`."
        )
    print(f"fournisseur exoscale {version}, au niveau du plancher {plancher} ou au-dessus")
    return version


def sorties_terraform(brut: dict[str, Any]) -> dict[str, Any]:
    """Ce que `terraform output -json` rend, débarrassé de son enveloppe.

    Chaque sortie arrive sous `{"value": ..., "type": ..., "sensitive": ...}` ;
    le reste du lanceur ne veut que la valeur.
    """
    return {nom: item["value"] for nom, item in brut.items()}


# ---- Les contrôles -----------------------------------------------------------


def inventaire(env: dict[str, str]) -> dict[str, Any]:
    """Le graphe que le plugin construit sur la plateforme déployée."""
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
    """Ce que l'inventaire doit avoir trouvé, comparé à ce que la stack a déployé.

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
            f"la stack en a déployé {attendu['total']}"
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
                f"la stack en a déployé {attendu[role]}"
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
    """Tout ce que la stack déclare, vérifié auprès de l'API par le SDK.

    Un contrôle qui se sert de la collection pour juger la collection ne mesure
    plus rien : ces lectures passent par le client officiel. Et un état
    Terraform qui s'accorde avec lui-même ne prouve pas qu'une plateforme
    existe : c'est l'API qui est interrogée.
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
    ids = sorties["ids"]
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
    sans_adresse = [m["name"] for m in machines if not m.get("public-ip")]
    exige(
        len(sans_adresse) == attendu["web"] + attendu["app"],
        f"{attendu['web'] + attendu['app']} machines sans adresse publique "
        f"({len(sans_adresse)} trouvées)",
    )
    bastion = client.get_instance(id=ids["instances"]["bastion"])
    exige(
        any(e.get("id") == ids["elastic_ip"] for e in bastion.get("elastic-ips") or ()),
        "le bastion porte l'adresse élastique de la stack",
    )
    reseaux = [
        r
        for r in client.list_private_networks().get("private-networks") or ()
        if r["name"].startswith(prefixe)
    ]
    exige(len(reseaux) == 2, f"deux réseaux privés ({len(reseaux)} trouvés)")
    backend = client.get_private_network(id=ids["private_networks"]["backend"])
    exige(
        len(backend.get("leases") or ()) == 5,
        f"cinq baux sur backend ({len(backend.get('leases') or ())})",
    )
    monitoring = client.get_private_network(id=ids["private_networks"]["monitoring"])
    exige(
        len(monitoring.get("leases") or ()) == attendu["app"],
        f"{attendu['app']} baux sur monitoring, un par machine applicative "
        f"({len(monitoring.get('leases') or ())})",
    )
    groupes = [
        g
        for g in client.list_security_groups().get("security-groups") or ()
        if g["name"].startswith(prefixe)
    ]
    exige(len(groupes) == 3, f"un groupe de sécurité par étage ({len(groupes)} trouvés)")
    aag = client.get_anti_affinity_group(id=ids["anti_affinity_group"])
    exige(
        len(aag.get("instances") or ()) == attendu["app"],
        f"le groupe d'anti-affinité porte les {attendu['app']} machines applicatives",
    )
    lb = client.get_load_balancer(id=ids["load_balancer"])
    services = list(lb.get("services") or [])
    exige(
        len(services) == 1
        and (services[0].get("instance-pool") or {}).get("id") == ids["instance_pool"],
        "un service sur le load balancer, vers le pool",
    )
    pool = client.get_instance_pool(id=ids["instance_pool"])
    exige(pool.get("size") == attendu["pool"], f"un pool de {attendu['pool']} machine")
    volume = client.get_block_storage_volume(id=ids["block_storage_volume"])
    exige(
        (volume.get("instance") or {}).get("id") == ids["instances"]["worker-b"],
        "le volume Block Storage est attaché à worker-b",
    )
    instantanes_block = [
        s
        for s in client.list_block_storage_snapshots().get("block-storage-snapshots") or ()
        if s["name"].startswith(prefixe)
    ]
    exige(len(instantanes_block) == 1, "un instantané Block Storage du volume")
    # Écarté, et dit. Le fournisseur 0.71.0 n'a aucune ressource d'instantané
    # d'instance, et la collection n'en crée pas : `create-snapshot` est
    # LIFECYCLE. Le contrôle ne se tait pas pour autant : il affirme l'absence,
    # sans quoi un instantané oublié un jour sur le compte passerait inaperçu.
    miens = {i["id"] for i in machines}
    instantanes = [
        s
        for s in client.list_snapshots().get("snapshots") or ()
        if (s.get("instance") or {}).get("id") in miens
    ]
    exige(
        len(instantanes) == 0,
        "aucun instantané d'instance : le fournisseur n'en crée pas, et il n'y en a pas",
    )
    print("plan de contrôle vérifié :")
    for constat in constats:
        print(f"  {constat}")


# ---- L'artefact ----------------------------------------------------------------


def artefact(
    journal: dict[str, Any],
    cible: str,
    run_id: str,
    residu: str,
    outillage: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Ce que cette exécution a couvert, dérivé de ce qui s'est réellement joué.

    **Joué n'est pas appelé.** Une tâche gardée par un `when` non satisfait ne
    touche jamais l'API, et une route que feint décline répond sans rien
    faire : ni l'une ni l'autre ne compte. Un module joué une fois et sauté
    ailleurs compte comme joué : la question est « a-t-il tourné contre cette
    API », pas « toutes ses tâches ont-elles tourné ».

    `outillage` dit avec quoi : la version de feint, de Terraform et du
    fournisseur. Un artefact qui ne nomme pas son instrument ne se relit pas.
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
        "outillage": dict(sorted((outillage or {}).items())),
    }


def ecrire_artefact(
    chemin_journal: Path,
    cible: str,
    run_id: str,
    residu: str,
    outillage: dict[str, str] | None = None,
) -> Path | None:
    """Écrit l'artefact à côté du journal. `None` quand rien n'a été journalisé :
    un artefact vide se lirait comme une exécution qui n'a rien couvert."""
    if not chemin_journal.is_file():
        return None
    journal = json.loads(chemin_journal.read_text(encoding="utf-8"))
    destination = TRAVAIL / f"{cible}-{run_id}.json"
    contenu = artefact(journal, cible, run_id, residu, outillage)
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


# ---- Le lanceur ------------------------------------------------------------------


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
    outillage = {"terraform": version_de([binaire("terraform"), "version"])}

    if cible["emulateur"]:
        outillage["feint"] = version_de([binaire("feint"), "version"])
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
        endpoint = env["EXOSCALE_API_ENDPOINT"]
    else:
        print("cible : l'organisation Exoscale réelle.")
        endpoint = ""
        if env.get("EXOSCALE_API_ENDPOINT"):
            # Dit plutôt que subi : un endpoint hérité du shell détournerait la
            # cible réelle vers autre chose, et le résidu serait vérifié là-bas.
            print(
                f"  EXOSCALE_API_ENDPOINT={env['EXOSCALE_API_ENDPOINT']} est dans l'environnement."
            )

    # Une seule zone pour la stack, l'inventaire et le contrôle de résidu :
    # contre l'émulateur, celle que `feint env` exporte ; sinon celle du shell.
    zone = env.get("EXOSCALE_ZONE") or ZONE_PAR_DEFAUT
    env["EXOSCALE_ZONE"] = zone
    env["TF_IN_AUTOMATION"] = "1"
    variables = {
        "run_id": run_id,
        "ssh_public_key": cle_ssh(),
        "endpoint": endpoint,
        "zone": zone,
    }

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

    code = 0
    try:
        if terraform("init", env, {}).returncode != 0:
            raise ExempleError("`terraform init` a échoué")
        # Avant le premier appel d'API, et après `init` : c'est lui qui résout.
        outillage["provider_exoscale"] = exiger_le_plancher(env)
        if terraform("apply", env, variables).returncode != 0:
            raise ExempleError("`terraform apply` a échoué")

        sorties = sorties_terraform(
            json.loads(terraform("output", env, {}, json_sortie=True).stdout or "{}")
        )
        print(
            f"plateforme déployée : {sorties['attendu']['total']} machines, "
            f"préfixe {sorties['prefixe']}, bastion {sorties['bastion_ip']}"
        )

        controler_plan_de_controle(env, sorties)
        controler_inventaire(inventaire(env), sorties)

        extra = {"cible": arguments.cible, "prefixe": sorties["prefixe"]}
        code = jouer("modules.yml", env, extra)
        return code
    finally:
        if arguments.garder:
            options = " ".join(f"-var {nom}='{valeur}'" for nom, valeur in variables.items())
            print(
                "\nplateforme conservée. La détruire avec :\n"
                f"  terraform -chdir=examples/stack destroy -auto-approve {options}"
            )
        else:
            print("\n--- destruction ---", flush=True)
            if terraform("destroy", env, variables).returncode != 0:
                print(
                    "LA DESTRUCTION A ÉCHOUÉ. Ne pas en rester là : relancer "
                    "`terraform -chdir=examples/stack destroy`, puis vérifier.",
                    file=sys.stderr,
                )
                code = 1
            verifier = [sys.executable, str(ROOT / "scripts" / "residue.py"), "verify"]
            if lancer(verifier, env=env).returncode != 0:
                code = 1
                verdict_residu = "non vérifié"
            else:
                verdict_residu = "aucun" if not cible["emulateur"] else "aucun (émulateur)"
        # Dans le `finally`, et après le contrôle de résidu : une exécution qui
        # a échoué au milieu a quand même couvert quelque chose, et c'est cette
        # trace-là qui manquait.
        ecrit = ecrire_artefact(journal, arguments.cible, run_id, verdict_residu, outillage)
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
