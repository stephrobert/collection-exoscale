#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Contrat de laboratoire (@lab)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : tests/fixtures/gadget/input/exoscale.v2.json
# Opérations : get-gadget-gizmo, list-gadget-gizmos
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: gadget_gizmo_info
short_description: Gather information about Exoscale gadget gizmos
version_added: 9.9.9
description:
- Read one Exoscale gadget gizmo by its identifier, or list them. This module never changes
  anything.
author:
- Contrat de laboratoire (@lab)
options:
  id:
    description: Not documented by the Exoscale API contract.
    type: str
    required: true
  gizmo_id:
    description: Not documented by the Exoscale API contract.
    type: str
extends_documentation_fragment:
- lab.gadget.exoscale
"""

EXAMPLES = r"""
- name: List gadget gizmos
  lab.gadget.gadget_gizmo_info:
    zone: ch-gva-2
  register: result
- name: Read one gadget gizmo
  lab.gadget.gadget_gizmo_info:
    zone: ch-gva-2
    gizmo_id: 11111111-2222-3333-4444-555555555555
  register: result
"""

RETURN = r"""
gadget_gizmo:
  description: The gadget gizmo, when a selector is given.
  returned: when the selector is given
  type: dict
gadget_gizmos:
  description: The gadget gizmos.
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
    "id": {"type": "str", "required": True},
    "gizmo_id": {"type": "str"},
}

#: Ce que le contrat exige pour une action et pas pour une autre.
REQUIRED_IF = []

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(exoscale_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = InfoModule(
    resource="gadget_gizmo",
    get_operation=Operation(
        id="get-gadget-gizmo",
        method="get_gadget_gizmo",
        path_params={"id": "id", "gizmo_id": "gizmo-id"},
    ),
    list_operation=Operation(
        id="list-gadget-gizmos",
        method="list_gadget_gizmos",
        path_params={"id": "id"},
        payload_field="gizmos",
        is_list=True,
    ),
    selector="gizmo_id",
)


def main() -> None:
    module = AnsibleModule(
        argument_spec=ARGUMENT_SPEC, required_if=REQUIRED_IF, supports_check_mode=True
    )
    run_info_module(module, MODULE)


if __name__ == "__main__":
    main()
