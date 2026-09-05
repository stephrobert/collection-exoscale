# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Stéphane Robert
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
name: compute
short_description: Exoscale compute dynamic inventory
version_added: 0.1.0
author:
  - Stéphane Robert (@stephrobert)
requirements:
  - exoscale >= 0.16
description:
  - Builds an Ansible inventory from an Exoscale organization.
  - >-
    Discovers instances zone by zone, then enriches them with their private
    network addresses by reading the leases of every private network of the
    zone, rather than one call per machine.
  - Uses a configuration file whose name ends with C(exoscale.yml) or C(exo.yml).
extends_documentation_fragment:
  - constructed
  - inventory_cache
notes:
  - >-
    The credential options are declared here rather than inherited from the
    module documentation fragment. A module option carries no C(env) key, so
    its default would silently win over the environment.
  - >-
    The API host carries the zone, so the plugin builds one client per zone.
    When I(api_url) is set, every zone talks to that host, which is what a
    local emulator expects.
options:
  plugin:
    description: The name of this plugin.
    required: true
    choices: ['stephrobert.exoscale.compute']
    type: str
  api_key:
    description: Exoscale API key.
    type: str
    required: true
    env:
      - name: EXOSCALE_API_KEY
  api_secret:
    description: Exoscale API secret.
    type: str
    required: true
    env:
      - name: EXOSCALE_API_SECRET
  api_url:
    description:
      - Full base URL of the API, C(/v2) included, replacing the one built from each zone.
      - Point it at a local emulator to build an inventory without a real account.
    type: str
    env:
      - name: EXOSCALE_API_URL
      - name: EXOSCALE_API_ENDPOINT
  products:
    description:
      - Products to discover hosts from.
      - C(all) means every host product this plugin version supports.
    type: list
    elements: str
    default: [all]
  zones:
    description:
      - Zones to query. Empty means every zone the API contract declares,
        or only I(default_zone) when I(api_url) is set.
    type: list
    elements: str
    default: []
  default_zone:
    description:
      - The zone an explicit I(api_url) serves.
      - >-
        The API host normally carries the zone, so an explicit URL reaches a
        single zone; querying every zone through it would list each machine
        once per zone. Used when I(api_url) is set and I(zones) is empty.
    type: str
    env:
      - name: EXOSCALE_ZONE
  hostnames:
    description:
      - Sources for C(inventory_hostname), in order of precedence.
      - >-
        Accepts C(name), C(id), C(public_ipv4), C(public_ipv6), C(private_ipv4),
        C(private_ipv6) and C(label:KEY), which reads the value of the label C(KEY).
      - Collisions are resolved by appending the zone, then the instance ID.
    type: list
    elements: str
    default: [name, id]
  address_priority:
    description:
      - Address families to try, in order, when setting C(ansible_host).
    type: list
    elements: str
    default: [private_ipv4, public_ipv4, private_ipv6, public_ipv6]
  address:
    description:
      - Restrict C(ansible_host) to one private network.
      - Accepts C(private_network), a name or an ID, or C(private_network_id).
    type: dict
    default: {}
  require_address:
    description:
      - Drop hosts for which no address could be selected.
      - >-
        False keeps them without C(ansible_host), which is still useful for
        tasks delegated to localhost that act through the Exoscale API.
    type: bool
    default: false
  labels:
    description:
      - Only keep hosts carrying these labels, as a C(key) to C(value) mapping.
      - An empty value keeps every host carrying the key, whatever its value.
    type: dict
    default: {}
  labels_match:
    description: Whether a host must carry any or all of the requested labels.
    type: str
    choices: [any, all]
    default: any
  states:
    description: Only keep hosts in these states.
    type: list
    elements: str
    default: []
  exclude:
    description:
      - Drop hosts matching these C(labels) or C(states), after every other filter.
    type: dict
    default: {}
  group_by:
    description:
      - Axes used to build the native C(exo_*) groups.
    type: list
    elements: str
    choices: [product, zone, state, labels, private_network, manager, type]
    default: [product, zone, state]
  include_raw:
    description:
      - Expose the raw API object as C(exoscale_raw). Off by default.
    type: bool
    default: false
  strict:
    description:
      - Fail the inventory when a provider fails, instead of warning.
    type: bool
    default: true
"""

EXAMPLES = r"""
# Le cas minimal : les identifiants viennent de l'environnement.
plugin: stephrobert.exoscale.compute

# Production : deux zones, les machines qui tournent, groupées par label.
# plugin: stephrobert.exoscale.compute
# zones:
#   - ch-gva-2
#   - de-fra-1
# states:
#   - running
# labels:
#   env: production
# group_by:
#   - product
#   - zone
#   - labels
#   - manager
# cache: true

# Joindre les machines par un réseau privé précis.
# plugin: stephrobert.exoscale.compute
# address:
#   private_network: backend
# require_address: true

# Groupes et variables construits par Ansible lui-même.
# plugin: stephrobert.exoscale.compute
# compose:
#   ansible_user: "'ubuntu'"
# keyed_groups:
#   - prefix: exo_type
#     key: exoscale_instance.type
"""

from ansible.errors import AnsibleError, AnsibleParserError
from ansible.module_utils.basic import missing_required_lib
from ansible.plugins.inventory import BaseInventoryPlugin, Cacheable, Constructable

from ansible_collections.stephrobert.exoscale.plugins.module_utils.inventory import (
    config as configuration,
)
from ansible_collections.stephrobert.exoscale.plugins.module_utils.inventory import (
    discovery,
    filtering,
)
from ansible_collections.stephrobert.exoscale.plugins.module_utils.inventory.address import (
    select_ansible_host,
)
from ansible_collections.stephrobert.exoscale.plugins.module_utils.inventory.groups import (
    group_names,
)
from ansible_collections.stephrobert.exoscale.plugins.module_utils.inventory.hostname import (
    assign_hostnames,
)
from ansible_collections.stephrobert.exoscale.plugins.module_utils.inventory.models import (
    InventoryHost,
    NetworkAttachment,
)
from ansible_collections.stephrobert.exoscale.plugins.module_utils.inventory.providers.base import (
    EXOSCALE_ZONES,
    DiscoveryContext,
)

#: Les suffixes que le plugin accepte pour son fichier de configuration.
ALLOWED_SUFFIXES = ("exoscale.yaml", "exoscale.yml", "exo.yaml", "exo.yml")


def _plain(valeur):
    """Réduit une valeur à des structures qu'un cache sait écrire.

    Le SDK rend du JSON, donc presque tout passe tel quel ; ce qui n'a pas
    d'équivalent JSON devient sa représentation textuelle plutôt que de faire
    échouer l'écriture du cache.
    """
    if valeur is None or isinstance(valeur, (str, int, float, bool)):
        return valeur
    if isinstance(valeur, dict):
        return {str(cle): _plain(item) for cle, item in valeur.items()}
    if isinstance(valeur, (list, tuple, set)):
        return [_plain(item) for item in valeur]
    return str(valeur)


class InventoryModule(BaseInventoryPlugin, Constructable, Cacheable):
    """Le dialogue avec Ansible, et rien d'autre.

    Toutes les décisions vivent dans `module_utils/inventory/`, en couches qui
    se testent seules. Ce fichier lit les options, appelle le moteur, et pose
    le résultat dans l'inventaire.
    """

    NAME = "stephrobert.exoscale.compute"

    def verify_file(self, path):
        if not super(InventoryModule, self).verify_file(path):
            return False
        if not path.endswith(ALLOWED_SUFFIXES):
            self.display.vvv(
                "Skipping due to inventory source file name mismatch. "
                "The file name has to end with one of: " + ", ".join(ALLOWED_SUFFIXES)
            )
            return False
        return True

    def parse(self, inventory, loader, path, cache=True):
        super(InventoryModule, self).parse(inventory, loader, path, cache)
        self._read_config_data(path)

        if not discovery.HAS_SDK:
            raise AnsibleError(missing_required_lib("exoscale"))

        try:
            settings = configuration.from_options(
                self.get_option, discovery.HOST_PROVIDERS, EXOSCALE_ZONES
            )
        except configuration.ConfigError as erreur:
            raise AnsibleParserError(str(erreur)) from erreur

        self.load_cache_plugin()
        empreinte = settings.cache_fingerprint(
            self.get_option("api_url"), self.get_option("api_key")
        )
        cache_key = "%s_%s" % (self.get_cache_key(path), empreinte)

        demande = self.get_option("cache")
        lire = demande and cache
        ecrire = demande and not cache

        materiel = None
        if lire:
            try:
                materiel = self._cache[cache_key]
                self.display.vvv("exoscale: cache hit (%s)" % cache_key)
            except KeyError:
                ecrire = True

        if materiel is None:
            materiel = self._collect(settings)
            self.display.vvv("exoscale: cache miss, découverte effectuée")

        if ecrire:
            self._cache[cache_key] = materiel

        self._populate(materiel, settings)

    def _collect(self, settings):
        """Découvre, enrichit, et rend une structure que n'importe quel cache accepte."""
        client_for = discovery.client_factory(
            self.get_option("api_key"), self.get_option("api_secret"), self.get_option("api_url")
        )
        # Avec une URL explicite, un seul hôte répond, donc une seule zone : la
        # parcourir huit fois listerait chaque machine huit fois. Mesuré contre
        # feint, qui ne sert qu'une zone par processus.
        zones = settings.zones
        if not zones:
            zone_par_defaut = self.get_option("default_zone")
            if self.get_option("api_url") and zone_par_defaut:
                zones = (str(zone_par_defaut),)
            elif self.get_option("api_url"):
                raise AnsibleParserError(
                    "api_url est donné sans zones ni default_zone : une URL explicite "
                    "sert une seule zone, et le plugin ne sait pas laquelle. Donner "
                    "`zones`, `default_zone`, ou EXOSCALE_ZONE."
                )
            else:
                zones = EXOSCALE_ZONES
        report = discovery.DiscoveryReport()

        # L'index réseau coûte une liste par zone plus une lecture par réseau,
        # et il ne sert qu'aux produits qui portent des réseaux privés.
        index = None
        if discovery.needs_network_index(settings.products):
            index = discovery.build_network_index(client_for, zones, report)
        else:
            self.display.vvv(
                "exoscale: aucun produit demandé ne joint de réseau privé, index non construit"
            )

        context = DiscoveryContext(
            zones=zones,
            include_raw=settings.include_raw,
            network=index,
        )

        resultat, decouverte = discovery.discover(
            client_for, context, settings.products, strict=settings.strict
        )
        report.api_calls += decouverte.api_calls
        report.providers.update(decouverte.providers)
        report.warnings.extend(decouverte.warnings)
        report.errors.extend(decouverte.errors)

        if settings.strict and report.errors:
            raise AnsibleError("la découverte a échoué : " + " ; ".join(report.errors))

        gardes = []
        ecartes = []
        for host in resultat.hosts:
            garde, raison = filtering.keep(host.labels, host.state, settings.filters)
            if garde:
                gardes.append(host)
            else:
                ecartes.append("%s (%s) : %s" % (host.name or host.id, host.product, raison))
        return {
            "hosts": [self._serialise(host) for host in gardes],
            "report": report.lines() + ["écartée : " + raison for raison in ecartes],
        }

    @staticmethod
    def _serialise(host):
        """Le modèle normalisé, en structures sérialisables."""
        return {
            "id": host.id,
            "product": host.product,
            "name": host.name,
            "zone": host.zone,
            "state": host.state,
            "labels": dict(host.labels),
            "public_ipv4": list(host.public_ipv4),
            "public_ipv6": list(host.public_ipv6),
            "private_ipv4": list(host.private_ipv4),
            "private_ipv6": list(host.private_ipv6),
            "private_networks": [a.to_variable() for a in host.private_networks],
            "manager_type": host.manager_type,
            "manager_id": host.manager_id,
            "metadata": _plain(dict(host.metadata)),
            "raw": _plain(host.raw),
        }

    @staticmethod
    def _deserialise(donnees):
        return InventoryHost(
            id=donnees["id"],
            product=donnees["product"],
            name=donnees.get("name"),
            zone=donnees.get("zone"),
            state=donnees.get("state"),
            labels=dict(donnees.get("labels") or {}),
            public_ipv4=tuple(donnees.get("public_ipv4") or ()),
            public_ipv6=tuple(donnees.get("public_ipv6") or ()),
            private_ipv4=tuple(donnees.get("private_ipv4") or ()),
            private_ipv6=tuple(donnees.get("private_ipv6") or ()),
            private_networks=tuple(
                NetworkAttachment(
                    private_network_id=reseau["id"],
                    private_network_name=reseau.get("name"),
                    ipv4=tuple(reseau.get("ipv4") or ()),
                    ipv6=tuple(reseau.get("ipv6") or ()),
                )
                for reseau in donnees.get("private_networks") or ()
            ),
            manager_type=donnees.get("manager_type"),
            manager_id=donnees.get("manager_id"),
            metadata=donnees.get("metadata") or {},
            raw=donnees.get("raw"),
        )

    def _populate(self, materiel, settings):
        """Pose les hosts, leurs variables et leurs groupes dans l'inventaire."""
        for ligne in materiel["report"]:
            self.display.vvv("exoscale: " + ligne)

        hosts = tuple(self._deserialise(donnees) for donnees in materiel["hosts"])
        attribues, collisions = assign_hostnames(hosts, settings.hostnames)
        for avertissement in collisions:
            self.display.warning("exoscale: " + avertissement)

        strict = settings.strict

        for host, nom in attribues:
            selection = select_ansible_host(host, settings.address)
            self.display.vvvv("exoscale: " + selection.explain(nom))

            if not selection.found and settings.require_address:
                self.display.warning("exoscale: %s écartée, %s" % (nom, selection.source))
                continue

            self.inventory.add_host(nom)
            if selection.found:
                self.inventory.set_variable(nom, "ansible_host", selection.address)

            variables = self._host_variables(host, selection)
            for cle, valeur in variables.items():
                self.inventory.set_variable(nom, cle, valeur)

            for groupe in group_names(host, settings.group_by):
                self.inventory.add_group(groupe)
                self.inventory.add_child(groupe, nom)

            # Les mécanismes natifs d'Ansible, appelés et non seulement hérités.
            self._set_composite_vars(self.get_option("compose"), variables, nom, strict)
            self._add_host_to_composed_groups(self.get_option("groups"), variables, nom, strict)
            self._add_host_to_keyed_groups(self.get_option("keyed_groups"), variables, nom, strict)

    @staticmethod
    def _host_variables(host, selection):
        """Les hostvars stables, celles sur lesquelles un playbook peut compter.

        `exoscale_id` et `exoscale_zone` sont ce qui permet d'enchaîner sur les
        modules Day-2 sans lookup supplémentaire.
        """
        variables = {
            "exoscale_id": host.id,
            "exoscale_product": host.product,
            "exoscale_name": host.name,
            "exoscale_zone": host.zone,
            "exoscale_state": host.state,
            "exoscale_labels": dict(host.labels),
            "exoscale_public_ipv4": list(host.public_ipv4),
            "exoscale_public_ipv6": list(host.public_ipv6),
            "exoscale_private_ipv4": list(host.private_ipv4),
            "exoscale_private_ipv6": list(host.private_ipv6),
            "exoscale_private_networks": [a.to_variable() for a in host.private_networks],
            "exoscale_manager_type": host.manager_type,
            "exoscale_manager_id": host.manager_id,
            "exoscale_address_source": selection.source,
        }
        if host.metadata:
            variables["exoscale_" + host.product] = dict(host.metadata)
        if host.raw is not None:
            variables["exoscale_raw"] = host.raw
        return variables
