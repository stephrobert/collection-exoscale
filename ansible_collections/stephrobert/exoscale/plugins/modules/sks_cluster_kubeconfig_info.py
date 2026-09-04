#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/exoscale/exoscale.v2.json
# Opérations : generate-sks-cluster-kubeconfig
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: sks_cluster_kubeconfig_info
short_description: Gather information about Exoscale sks cluster kubeconfigs
version_added: 0.1.0
description:
- Read one Exoscale sks cluster kubeconfig. This module never changes anything.
author:
- Stéphane Robert (@stephrobert)
options:
  id:
    description: Not documented by the Exoscale API contract.
    type: str
    required: true
  ttl:
    description: 'Validity in seconds of the Kubeconfig user certificate (default: 30 days)'
    type: int
  user:
    description: User name in the generated Kubeconfig. The certificate present in the Kubeconfig
      will also have this name set for the CN field.
    type: str
  groups:
    description: List of roles. The certificate present in the Kubeconfig will have these
      roles set in the Org field.
    type: list
    elements: str
extends_documentation_fragment:
- stephrobert.exoscale.exoscale
notes:
- 'The returned value is a secret: do not log the task output.'
"""

EXAMPLES = r"""
- name: Read one sks cluster kubeconfig
  stephrobert.exoscale.sks_cluster_kubeconfig_info:
    zone: ch-gva-2
    id: 11111111-2222-3333-4444-555555555555
  register: result
"""

RETURN = r"""
sks_cluster_kubeconfig:
  description: The sks cluster kubeconfig.
  returned: always
  type: dict
"""

from ansible.module_utils.basic import AnsibleModule  # noqa: E402

from ansible_collections.stephrobert.exoscale.plugins.module_utils.exoscale import (  # noqa: E402
    InfoModule,
    Operation,
    exoscale_argument_spec,
    run_info_module,
)

#: Options propres au module, traduites depuis le contrat.
MODULE_ARGUMENT_SPEC = {
    "id": {"type": "str", "required": True},
    "ttl": {"type": "int"},
    "user": {"type": "str"},
    "groups": {"type": "list", "elements": "str"},
}

#: Ce que le contrat exige pour une action et pas pour une autre.
REQUIRED_IF = []

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(exoscale_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = InfoModule(
    resource="sks_cluster_kubeconfig",
    get_operation=Operation(
        id="generate-sks-cluster-kubeconfig",
        method="generate_sks_cluster_kubeconfig",
        path_params={"id": "id"},
        body_params={"ttl": "ttl", "user": "user", "groups": "groups"},
        payload_field="kubeconfig",
    ),
)


def main() -> None:
    module = AnsibleModule(
        argument_spec=ARGUMENT_SPEC, required_if=REQUIRED_IF, supports_check_mode=True
    )
    run_info_module(module, MODULE)


if __name__ == "__main__":
    main()
