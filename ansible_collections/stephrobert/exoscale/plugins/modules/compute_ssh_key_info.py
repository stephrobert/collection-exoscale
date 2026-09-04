#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/exoscale/exoscale.v2.json
# Opérations : get-ssh-key, list-ssh-keys
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: compute_ssh_key_info
short_description: Gather information about Exoscale ssh keys
version_added: 0.1.0
description:
- Read one Exoscale ssh key by its identifier, or list them. This module never changes anything.
author:
- Stéphane Robert (@stephrobert)
options:
  name:
    description: Not documented by the Exoscale API contract.
    type: str
extends_documentation_fragment:
- stephrobert.exoscale.exoscale
"""

EXAMPLES = r"""
- name: List ssh keys
  stephrobert.exoscale.compute_ssh_key_info:
    zone: ch-gva-2
  register: result
- name: Read one ssh key
  stephrobert.exoscale.compute_ssh_key_info:
    zone: ch-gva-2
    name: 11111111-2222-3333-4444-555555555555
  register: result
"""

RETURN = r"""
ssh_key:
  description: The ssh key, when a selector is given.
  returned: when the selector is given
  type: dict
ssh_keys:
  description: The ssh keys.
  returned: when no selector is given
  type: list
  elements: dict
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
    "name": {"type": "str"},
}

#: Ce que le contrat exige pour une action et pas pour une autre.
REQUIRED_IF = []

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(exoscale_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = InfoModule(
    resource="ssh_key",
    get_operation=Operation(
        id="get-ssh-key",
        method="get_ssh_key",
        path_params={"name": "name"},
    ),
    list_operation=Operation(
        id="list-ssh-keys",
        method="list_ssh_keys",
        path_params={},
        payload_field="ssh-keys",
        is_list=True,
    ),
    selector="name",
)


def main() -> None:
    module = AnsibleModule(
        argument_spec=ARGUMENT_SPEC, required_if=REQUIRED_IF, supports_check_mode=True
    )
    run_info_module(module, MODULE)


if __name__ == "__main__":
    main()
