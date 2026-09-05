"""La plateforme d'exemple : bâtie et détruite par le SDK Exoscale, sans état local.

**Pourquoi le SDK et pas Terraform.** `feint env exoscale` prévient que le
fournisseur Terraform d'Exoscale n'honore `EXOSCALE_API_ENDPOINT` que pour son
client egoscale v3, pas pour le v2 : un `apply` se partagerait entre
l'émulateur et le vrai cloud, avec de vrais identifiants dans l'environnement.
Mesuré par feint (#525), et refusé par lui. Le SDK Python honore l'URL de bout
en bout, donc la même plateforme se bâtit à l'identique contre feint et contre
le compte réel, et le seul endpoint change.

**Pourquoi aucun état local.** Tout ce que la plateforme crée porte le label
`exemple=<run_id>`, et la destruction **relit l'API** pour trouver ce qu'elle
doit emporter : un `apply` interrompu au milieu se détruit aussi bien qu'un
`apply` complet, parce que la vérité est chez l'API, pas dans un fichier. Les
ressources que l'API ne sait pas étiqueter (clé SSH, instantanés) portent le
préfixe `exo-<run_id>` dans leur nom.

**Ce qu'elle contient**, et pourquoi cette forme :

* un bastion, seule machine à porter une adresse élastique ;
* deux machines web et deux machines applicatives sans adresse publique, sur
  un réseau privé géré `backend`, les applicatives aussi sur `monitoring` et
  dans un groupe d'anti-affinité : c'est ce qui donne au plugin d'inventaire
  quelque chose à prouver, quatre machines sur cinq n'ont que des baux ;
* un pool d'instances d'une machine et un load balancer qui le sert : les
  modules de pool et de load balancer ont une cible ;
* un instantané d'une machine applicative, un volume Block Storage attaché à
  l'autre et son instantané : les modules d'instantané et de stockage aussi.

    python examples/stack/platform.py apply   --run-id 42ab --ssh-public-key "ssh-ed25519 ..."
    python examples/stack/platform.py destroy --run-id 42ab
    python examples/stack/platform.py output  --run-id 42ab

Les identifiants et l'endpoint viennent de l'environnement : `EXOSCALE_API_KEY`,
`EXOSCALE_API_SECRET`, `EXOSCALE_API_ENDPOINT` (ou `EXOSCALE_API_URL`) et
`EXOSCALE_ZONE`, ce que `feint env exoscale` exporte.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections.abc import Callable
from typing import Any

from exoscale.api.exceptions import ExoscaleAPIException
from exoscale.api.v2 import Client

#: Le label que porte tout ce que la plateforme crée.
LABEL = "exemple"

#: Les rôles, et ce que chaque machine porte. Les machines applicatives sont
#: sur deux réseaux : c'est ce qui prouve que l'inventaire sait choisir.
MACHINES: tuple[dict[str, Any], ...] = (
    {"nom": "bastion", "role": "bastion", "reseaux": ("backend",), "eip": True},
    {"nom": "web-1", "role": "web", "reseaux": ("backend",)},
    {"nom": "web-2", "role": "web", "reseaux": ("backend",)},
    {"nom": "worker-a", "role": "app", "reseaux": ("backend", "monitoring"), "anti_affinite": True},
    {"nom": "worker-b", "role": "app", "reseaux": ("backend", "monitoring"), "anti_affinite": True},
)

#: Les réseaux privés gérés : une plage, pour que l'API distribue des baux.
RESEAUX: dict[str, dict[str, str]] = {
    "backend": {"start_ip": "10.42.0.10", "end_ip": "10.42.0.250", "netmask": "255.255.255.0"},
    "monitoring": {"start_ip": "10.43.0.10", "end_ip": "10.43.0.250", "netmask": "255.255.255.0"},
}

#: Les tailles acceptables, de la plus petite à la plus grande : la première
#: que la zone propose est prise. Le nom est celui du contrat (`family.size`).
TAILLES: tuple[str, ...] = ("standard.tiny", "standard.micro", "standard.small")


class PlatformError(RuntimeError):
    """La plateforme ne peut pas être bâtie ou détruite, et il faut le dire."""


def client_from_env() -> Client:
    cle = os.environ.get("EXOSCALE_API_KEY")
    secret = os.environ.get("EXOSCALE_API_SECRET")
    if not cle or not secret:
        raise PlatformError(
            "EXOSCALE_API_KEY et EXOSCALE_API_SECRET sont requis dans l'environnement"
        )
    url = os.environ.get("EXOSCALE_API_URL") or os.environ.get("EXOSCALE_API_ENDPOINT")
    if url:
        return Client(cle, secret, url=url)
    zone = os.environ.get("EXOSCALE_ZONE")
    if not zone:
        raise PlatformError("EXOSCALE_ZONE est requis quand aucune URL d'API n'est donnée")
    return Client(cle, secret, zone=zone)


def zone_from_env() -> str:
    return os.environ.get("EXOSCALE_ZONE") or "ch-gva-2"


class Platform:
    """Une plateforme identifiée par son `run_id`, bâtie ou détruite par l'API."""

    def __init__(self, client: Client, run_id: str) -> None:
        self.client = client
        self.run_id = run_id
        self.prefixe = f"exo-{run_id}"
        self.labels = {LABEL: run_id}

    # --- l'attente, et ce qu'elle rend ---------------------------------------

    def attendre(self, operation: dict[str, Any], quoi: str) -> str | None:
        """Attend la fin d'une opération, et rend l'identifiant de la ressource."""
        if not isinstance(operation, dict) or "id" not in operation:
            raise PlatformError(f"{quoi} : l'API n'a pas rendu d'opération ({operation!r})")
        try:
            fini = self.client.wait(operation["id"], max_wait_time=600)
        except ExoscaleAPIException as erreur:
            raise PlatformError(f"{quoi} : {erreur}") from erreur
        reference = fini.get("reference") or {}
        identifiant = reference.get("id")
        return str(identifiant) if identifiant else None

    def _appartient(self, ressource: dict[str, Any]) -> bool:
        """Par le label, sinon par le nom, sinon par la description.

        Une adresse élastique n'a pas de nom, et feint ne rend pas ses labels :
        la première destruction en a laissé une derrière elle, et c'est le
        contrôle de résidu, joué contre l'émulateur, qui l'a dit. La
        description porte donc le préfixe aussi, et `destroy` reconnaît en
        plus une adresse par la machine qui la porte.
        """
        labels = ressource.get("labels") or {}
        if labels.get(LABEL) == self.run_id:
            return True
        for champ in ("name", "description"):
            if str(ressource.get(champ) or "").startswith(self.prefixe):
                return True
        return False

    def _miens(self, liste: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
        return [item for item in liste or () if self._appartient(item)]

    # --- ce qu'il faut savoir avant de bâtir --------------------------------

    def template(self) -> dict[str, Any]:
        """Le premier modèle Ubuntu public, sans en supposer le nom exact."""
        modeles = self.client.list_templates().get("templates") or []
        for modele in modeles:
            if (modele.get("family") or "").lower() == "ubuntu":
                return modele
        if modeles:
            return modeles[0]
        raise PlatformError("aucun modèle d'instance dans cette zone")

    def instance_type(self) -> dict[str, Any]:
        """La plus petite taille que la zone propose, parmi celles acceptables."""
        types = self.client.list_instance_types().get("instance-types") or []
        par_nom = {
            f"{t.get('family')}.{t.get('size')}": t for t in types if t.get("authorized", True)
        }
        for taille in TAILLES:
            if taille in par_nom:
                return par_nom[taille]
        raise PlatformError(
            f"aucune des tailles {TAILLES} n'est proposée ; disponibles : {sorted(par_nom)}"
        )

    # --- bâtir ----------------------------------------------------------------

    def apply(self, ssh_public_key: str) -> dict[str, Any]:
        """Bâtit la plateforme et rend ses sorties. Idempotent par label : ce qui
        existe déjà pour ce `run_id` n'est pas recréé."""
        c = self.client
        sorties: dict[str, Any] = {
            "run_id": self.run_id,
            "prefixe": self.prefixe,
            "zone": zone_from_env(),
            "ids": {},
        }

        nom_cle = f"{self.prefixe}-cle"
        if not any(k.get("name") == nom_cle for k in c.list_ssh_keys().get("ssh-keys") or ()):
            self.attendre(c.register_ssh_key(name=nom_cle, public_key=ssh_public_key), "clé SSH")
        sorties["ids"]["ssh_key"] = nom_cle

        groupes: dict[str, str] = {}
        existants = {
            g["name"]: g for g in self._miens(c.list_security_groups().get("security-groups"))
        }
        for role, ports in (("bastion", (22,)), ("web", (22, 80)), ("app", (22, 8080))):
            nom = f"{self.prefixe}-{role}"
            if nom in existants:
                groupes[role] = str(existants[nom]["id"])
                continue
            identifiant = self.attendre(
                c.create_security_group(name=nom, description=f"étage {role} de {self.prefixe}"),
                f"groupe de sécurité {role}",
            )
            for port in ports:
                self.attendre(
                    c.add_rule_to_security_group(
                        id=identifiant,
                        flow_direction="ingress",
                        protocol="tcp",
                        start_port=port,
                        end_port=port,
                        network="0.0.0.0/0",
                    ),
                    f"règle {port} de {role}",
                )
            groupes[role] = str(identifiant)
        sorties["ids"]["security_groups"] = groupes

        aag_nom = f"{self.prefixe}-app"
        aags = self._miens(c.list_anti_affinity_groups().get("anti-affinity-groups"))
        aag_id = next((str(g["id"]) for g in aags if g.get("name") == aag_nom), None)
        if aag_id is None:
            aag_id = self.attendre(
                c.create_anti_affinity_group(
                    name=aag_nom, description=f"tier applicatif de {self.prefixe}"
                ),
                "groupe d'anti-affinité",
            )
        sorties["ids"]["anti_affinity_group"] = aag_id

        reseaux: dict[str, str] = {}
        existants = {
            r["name"]: r for r in self._miens(c.list_private_networks().get("private-networks"))
        }
        for nom_court, plage in RESEAUX.items():
            nom = f"{self.prefixe}-{nom_court}"
            if nom in existants:
                reseaux[nom_court] = str(existants[nom]["id"])
                continue
            reseaux[nom_court] = str(
                self.attendre(
                    c.create_private_network(name=nom, labels=self.labels, **plage),
                    f"réseau {nom_court}",
                )
            )
        sorties["ids"]["private_networks"] = reseaux

        modele = self.template()
        taille = self.instance_type()
        sorties["template"] = modele.get("name")
        sorties["instance_type"] = f"{taille.get('family')}.{taille.get('size')}"

        instances: dict[str, str] = {}
        existantes = {i["name"]: i for i in self._miens(c.list_instances().get("instances"))}
        for machine in MACHINES:
            nom = f"{self.prefixe}-{machine['nom']}"
            if nom in existantes:
                instances[machine["nom"]] = str(existantes[nom]["id"])
                continue
            corps: dict[str, Any] = {
                "name": nom,
                "instance_type": {"id": taille["id"]},
                "template": {"id": modele["id"]},
                "disk_size": 10,
                "ssh_key": {"name": nom_cle},
                "security_groups": [{"id": groupes[machine["role"]]}],
                "labels": {**self.labels, "role": machine["role"]},
                "public_ip_assignment": "inet4" if machine.get("eip") else "none",
            }
            if machine.get("anti_affinite"):
                corps["anti_affinity_groups"] = [{"id": aag_id}]
            identifiant = self.attendre(c.create_instance(**corps), f"instance {machine['nom']}")
            instances[machine["nom"]] = str(identifiant)
            for reseau in machine["reseaux"]:
                self.attendre(
                    c.attach_instance_to_private_network(
                        id=reseaux[reseau], instance={"id": identifiant}
                    ),
                    f"rattachement de {machine['nom']} à {reseau}",
                )
        sorties["ids"]["instances"] = instances

        eips = self._miens(c.list_elastic_ips().get("elastic-ips"))
        eip_id = str(eips[0]["id"]) if eips else None
        if eip_id is None:
            eip_id = str(
                self.attendre(
                    c.create_elastic_ip(labels=self.labels, description=f"{self.prefixe}-bastion"),
                    "adresse élastique",
                )
            )
            self.attendre(
                c.attach_instance_to_elastic_ip(id=eip_id, instance={"id": instances["bastion"]}),
                "rattachement de l'adresse au bastion",
            )
        sorties["ids"]["elastic_ip"] = eip_id
        sorties["bastion_ip"] = (c.get_elastic_ip(id=eip_id) or {}).get("ip")

        pool_nom = f"{self.prefixe}-pool"
        pools = self._miens(c.list_instance_pools().get("instance-pools"))
        pool_id = next((str(p["id"]) for p in pools if p.get("name") == pool_nom), None)
        if pool_id is None:
            pool_id = str(
                self.attendre(
                    c.create_instance_pool(
                        name=pool_nom,
                        instance_type={"id": taille["id"]},
                        template={"id": modele["id"]},
                        size=1,
                        disk_size=10,
                        ssh_key={"name": nom_cle},
                        security_groups=[{"id": groupes["web"]}],
                        instance_prefix=f"{self.prefixe}-pool",
                        labels={**self.labels, "role": "pool"},
                    ),
                    "pool d'instances",
                )
            )
        sorties["ids"]["instance_pool"] = pool_id

        lb_nom = f"{self.prefixe}-lb"
        lbs = self._miens(c.list_load_balancers().get("load-balancers"))
        lb_id = next((str(lb["id"]) for lb in lbs if lb.get("name") == lb_nom), None)
        if lb_id is None:
            lb_id = str(
                self.attendre(
                    c.create_load_balancer(name=lb_nom, labels=self.labels), "load balancer"
                )
            )
            self.attendre(
                c.add_service_to_load_balancer(
                    id=lb_id,
                    name="web",
                    instance_pool={"id": pool_id},
                    protocol="tcp",
                    port=80,
                    target_port=80,
                    strategy="round-robin",
                    healthcheck={
                        "mode": "tcp",
                        "port": 80,
                        "interval": 10,
                        "timeout": 5,
                        "retries": 1,
                    },
                ),
                "service du load balancer",
            )
        lb = c.get_load_balancer(id=lb_id) or {}
        sorties["ids"]["load_balancer"] = lb_id
        sorties["ids"]["load_balancer_service"] = next(
            (str(s["id"]) for s in lb.get("services") or () if s.get("id")), None
        )
        sorties["application_url"] = f"http://{lb.get('ip')}" if lb.get("ip") else None

        snapshots = [
            s
            for s in c.list_snapshots().get("snapshots") or ()
            if (s.get("instance") or {}).get("id") == instances["worker-a"]
        ]
        snapshot_id = str(snapshots[0]["id"]) if snapshots else None
        if snapshot_id is None:
            snapshot_id = str(
                self.attendre(c.create_snapshot(id=instances["worker-a"]), "instantané de worker-a")
            )
        sorties["ids"]["snapshot"] = snapshot_id

        volume_nom = f"{self.prefixe}-data"
        volumes = self._miens(c.list_block_storage_volumes().get("block-storage-volumes"))
        volume_id = next((str(v["id"]) for v in volumes if v.get("name") == volume_nom), None)
        if volume_id is None:
            volume_id = str(
                self.attendre(
                    c.create_block_storage_volume(name=volume_nom, size=10, labels=self.labels),
                    "volume Block Storage",
                )
            )
            self.attendre(
                c.attach_block_storage_volume_to_instance(
                    id=volume_id, instance={"id": instances["worker-b"]}
                ),
                "rattachement du volume à worker-b",
            )
            self.attendre(
                c.create_block_storage_snapshot(
                    id=volume_id, name=f"{volume_nom}-snap", labels=self.labels
                ),
                "instantané du volume",
            )
        sorties["ids"]["block_storage_volume"] = volume_id
        snaps = self._miens(c.list_block_storage_snapshots().get("block-storage-snapshots"))
        sorties["ids"]["block_storage_snapshot"] = next((str(s["id"]) for s in snaps), None)

        sorties["attendu"] = {
            "bastion": 1,
            "web": 2,
            "app": 2,
            "pool": 1,
            "total": len(MACHINES) + 1,
        }
        return sorties

    # --- détruire -------------------------------------------------------------

    def destroy(self) -> list[str]:
        """Détruit tout ce qui porte le label ou le préfixe, dans l'ordre inverse
        des dépendances, en relisant l'API à chaque étape. Rend ce qui a été
        emporté, et lève sur ce qui n'a pas pu l'être."""
        c = self.client
        emportes: list[str] = []
        echecs: list[str] = []

        def supprimer(quoi: str, appel: Callable[[], Any]) -> None:
            try:
                self.attendre(appel(), quoi)
                emportes.append(quoi)
            except (ExoscaleAPIException, PlatformError) as erreur:
                echecs.append(f"{quoi} : {erreur}")

        for lb in self._miens(c.list_load_balancers().get("load-balancers")):
            supprimer(
                f"load balancer {lb['name']}", lambda i=lb["id"]: c.delete_load_balancer(id=i)
            )
        for pool in self._miens(c.list_instance_pools().get("instance-pools")):
            supprimer(f"pool {pool['name']}", lambda i=pool["id"]: c.delete_instance_pool(id=i))

        miennes = self._miens(c.list_instances().get("instances"))
        mes_ids = {str(i["id"]) for i in miennes}
        # Les adresses que mes machines portent sont miennes, quoi que l'API
        # rende de leurs labels.
        mes_eips = {
            str(e["id"]) for i in miennes for e in i.get("elastic-ips") or () if e.get("id")
        }

        def mon_adresse(eip: dict[str, Any]) -> bool:
            return self._appartient(eip) or str(eip.get("id")) in mes_eips

        for snap in self._miens(c.list_block_storage_snapshots().get("block-storage-snapshots")):
            supprimer(
                f"instantané Block {snap.get('name')}",
                lambda i=snap["id"]: c.delete_block_storage_snapshot(id=i),
            )
        for volume in self._miens(c.list_block_storage_volumes().get("block-storage-volumes")):
            if volume.get("instance"):
                supprimer(
                    f"détachement du volume {volume['name']}",
                    lambda i=volume["id"]: c.detach_block_storage_volume(id=i),
                )
            supprimer(
                f"volume {volume['name']}",
                lambda i=volume["id"]: c.delete_block_storage_volume(id=i),
            )

        for snap in c.list_snapshots().get("snapshots") or ():
            if (snap.get("instance") or {}).get("id") in mes_ids or self._appartient(snap):
                supprimer(
                    f"instantané {snap.get('name')}", lambda i=snap["id"]: c.delete_snapshot(id=i)
                )

        for eip in filter(mon_adresse, c.list_elastic_ips().get("elastic-ips") or ()):
            for instance in miennes:
                if any(e.get("id") == eip["id"] for e in instance.get("elastic-ips") or ()):
                    supprimer(
                        f"détachement de l'adresse {eip.get('ip')}",
                        lambda e=eip["id"], i=instance["id"]: c.detach_instance_from_elastic_ip(
                            id=e, instance={"id": i}
                        ),
                    )
        for instance in miennes:
            supprimer(
                f"instance {instance['name']}", lambda i=instance["id"]: c.delete_instance(id=i)
            )
        for eip in filter(mon_adresse, c.list_elastic_ips().get("elastic-ips") or ()):
            supprimer(f"adresse {eip.get('ip')}", lambda i=eip["id"]: c.delete_elastic_ip(id=i))
        for reseau in self._miens(c.list_private_networks().get("private-networks")):
            supprimer(
                f"réseau {reseau['name']}", lambda i=reseau["id"]: c.delete_private_network(id=i)
            )
        for aag in self._miens(c.list_anti_affinity_groups().get("anti-affinity-groups")):
            supprimer(
                f"anti-affinité {aag['name']}",
                lambda i=aag["id"]: c.delete_anti_affinity_group(id=i),
            )
        for groupe in self._miens(c.list_security_groups().get("security-groups")):
            supprimer(
                f"groupe de sécurité {groupe['name']}",
                lambda i=groupe["id"]: c.delete_security_group(id=i),
            )
        for cle in c.list_ssh_keys().get("ssh-keys") or ():
            if str(cle.get("name") or "").startswith(self.prefixe):
                supprimer(f"clé SSH {cle['name']}", lambda n=cle["name"]: c.delete_ssh_key(name=n))

        if echecs:
            raise PlatformError(
                f"{len(echecs)} suppression(s) ont échoué, {len(emportes)} ont abouti :\n  "
                + "\n  ".join(echecs)
            )
        return emportes


def main(argv: list[str]) -> int:
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument("action", choices=("apply", "destroy"))
    parseur.add_argument("--run-id", required=True)
    parseur.add_argument("--ssh-public-key", default="")
    parseur.add_argument("--output", default=None, help="fichier JSON des sorties (apply)")
    arguments = parseur.parse_args(argv[1:])

    plateforme = Platform(client_from_env(), arguments.run_id)
    debut = time.monotonic()
    if arguments.action == "apply":
        if not arguments.ssh_public_key:
            raise PlatformError("--ssh-public-key est requis pour apply")
        sorties = plateforme.apply(arguments.ssh_public_key)
        texte = json.dumps(sorties, indent=2, ensure_ascii=False, sort_keys=True)
        if arguments.output:
            with open(arguments.output, "w", encoding="utf-8") as handle:
                handle.write(texte + "\n")
        print(texte)
        print(f"plateforme bâtie en {time.monotonic() - debut:.1f} s", file=sys.stderr)
        return 0
    emportes = plateforme.destroy()
    print(f"{len(emportes)} ressource(s) détruite(s) en {time.monotonic() - debut:.1f} s")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv))
    except PlatformError as erreur:
        print(f"erreur : {erreur}", file=sys.stderr)
        raise SystemExit(1) from erreur
