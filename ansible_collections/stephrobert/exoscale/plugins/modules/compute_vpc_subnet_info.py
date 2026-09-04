#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/exoscale/exoscale.v2.json
# Opérations : get-subnet, list-subnets
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: compute_vpc_subnet_info
short_description: Gather information about Exoscale vpc subnets
version_added: 0.1.0
description:
- Read one Exoscale vpc subnet by its identifier, or list them. This module never changes
  anything.
author:
- Stéphane Robert (@stephrobert)
options:
  vpc_id:
    description: Not documented by the Exoscale API contract.
    type: str
    required: true
  id:
    description: Not documented by the Exoscale API contract.
    type: str
extends_documentation_fragment:
- stephrobert.exoscale.exoscale
"""

EXAMPLES = r"""
- name: List vpc subnets
  stephrobert.exoscale.compute_vpc_subnet_info:
    zone: ch-gva-2
  register: result
- name: Read one vpc subnet
  stephrobert.exoscale.compute_vpc_subnet_info:
    zone: ch-gva-2
    id: 11111111-2222-3333-4444-555555555555
  register: result
"""

RETURN = r"""
vpc_subnet:
  description: The vpc subnet, when a selector is given.
  returned: when the selector is given
  type: dict
vpc_subnets:
  description: The vpc subnets.
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
    "vpc_id": {"type": "str", "required": True},
    "id": {"type": "str"},
}

#: Ce que le contrat exige pour une action et pas pour une autre.
REQUIRED_IF = []

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(exoscale_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = InfoModule(
    resource="vpc_subnet",
    get_operation=Operation(
        id="get-subnet",
        method="get_subnet",
        path_params={"vpc_id": "vpc-id", "id": "id"},
    ),
    list_operation=Operation(
        id="list-subnets",
        method="list_subnets",
        path_params={"vpc_id": "vpc-id"},
        payload_field="subnets",
        is_list=True,
    ),
    selector="id",
)


def main() -> None:
    module = AnsibleModule(
        argument_spec=ARGUMENT_SPEC, required_if=REQUIRED_IF, supports_check_mode=True
    )
    run_info_module(module, MODULE)


if __name__ == "__main__":
    main()
