#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Contrat de laboratoire (@lab)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : tests/fixtures/gadget/input/exoscale.v2.json
# Opérations : get-gadget, list-gadgets
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: gadget_gadget_info
short_description: Gather information about Exoscale gadgets
version_added: 9.9.9
description:
- Read one Exoscale gadget by its identifier, or list them. This module never changes anything.
author:
- Contrat de laboratoire (@lab)
options:
  id:
    description: Not documented by the Exoscale API contract.
    type: str
  labels:
    description: Not documented by the Exoscale API contract.
    type: dict
extends_documentation_fragment:
- lab.gadget.exoscale
"""

EXAMPLES = r"""
- name: List gadgets
  lab.gadget.gadget_gadget_info:
    zone: ch-gva-2
  register: result
- name: Read one gadget
  lab.gadget.gadget_gadget_info:
    zone: ch-gva-2
    id: 11111111-2222-3333-4444-555555555555
  register: result
"""

RETURN = r"""
gadget:
  description: The gadget, when a selector is given.
  returned: when the selector is given
  type: dict
gadgets:
  description: The gadgets.
  returned: when no selector is given
  type: list
  elements: dict
"""

from ansible.module_utils.basic import AnsibleModule  # noqa: E402

from ansible_collections.lab.gadget.plugins.module_utils.exoscale import (  # noqa: E402
    InfoModule,
    Operation,
    exoscale_argument_spec,
    run_info_module,
)

#: Options propres au module, traduites depuis le contrat.
MODULE_ARGUMENT_SPEC = {
    "id": {"type": "str"},
    "labels": {"type": "dict"},
}

#: Ce que le contrat exige pour une action et pas pour une autre.
REQUIRED_IF = []

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(exoscale_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = InfoModule(
    resource="gadget",
    get_operation=Operation(
        id="get-gadget",
        method="get_gadget",
        path_params={"id": "id"},
    ),
    list_operation=Operation(
        id="list-gadgets",
        method="list_gadgets",
        path_params={},
        query_params={"labels": "labels"},
        payload_field="gadgets",
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
