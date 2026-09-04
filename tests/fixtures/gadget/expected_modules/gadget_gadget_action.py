#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Contrat de laboratoire (@lab)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : tests/fixtures/gadget/input/exoscale.v2.json
# Opérations : reset-gadget-field, revert-gadget-to-snapshot, scale-gadget, start-gadget
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: gadget_gadget_action
short_description: Perform an action on an Exoscale gadget
version_added: 9.9.9
description:
- 'Trigger one of the following actions on an existing gadget: C(reset_field), C(revert_to_snapshot),
  C(scale), C(start).'
author:
- Contrat de laboratoire (@lab)
options:
  action:
    description: The action to trigger on the gadget.
    type: str
    required: true
    choices:
    - reset_field
    - revert_to_snapshot
    - scale
    - start
  id:
    description: Not documented by the Exoscale API contract.
    type: str
    required: true
  field:
    description: Not documented by the Exoscale API contract.
    type: str
    choices:
    - labels
    - user-data
  snapshot_id:
    description: Snapshot ID
    type: str
  gadget_type:
    description: Not documented by the Exoscale API contract.
    type: dict
  rescue_profile:
    description: Boot in rescue mode
    type: str
    choices:
    - netboot
    - netboot-efi
extends_documentation_fragment:
- lab.gadget.exoscale
- lab.gadget.exoscale.wait
notes:
- 'Every action is asynchronous on the Exoscale API: the module waits for the returned operation
  to reach C(success) when I(wait) is true, and returns the operation as accepted otherwise.'
"""

EXAMPLES = r"""
- name: Run reset_field on a gadget
  lab.gadget.gadget_gadget_action:
    zone: ch-gva-2
    action: reset_field
    id: 11111111-2222-3333-4444-555555555555
"""

RETURN = r"""
operation:
  description: 'The Exoscale operation object: its C(state) is C(success) once the work is
    done, C(pending) when the module did not wait.'
  returned: always
  type: dict
"""

from ansible.module_utils.basic import AnsibleModule  # noqa: E402

from ansible_collections.lab.gadget.plugins.module_utils.exoscale import (  # noqa: E402
    Action,
    ActionModule,
    Operation,
    exoscale_argument_spec,
    exoscale_waitable_argument_spec,
    run_action_module,
)

#: Options propres au module, traduites depuis le contrat.
MODULE_ARGUMENT_SPEC = {
    "action": {
        "type": "str",
        "required": True,
        "choices": ["reset_field", "revert_to_snapshot", "scale", "start"],
    },
    "id": {"type": "str", "required": True},
    "field": {
        "type": "str",
        "choices": ["labels", "user-data"],
    },
    "snapshot_id": {"type": "str"},
    "gadget_type": {"type": "dict"},
    "rescue_profile": {
        "type": "str",
        "choices": ["netboot", "netboot-efi"],
    },
}

#: Ce que le contrat exige pour une action et pas pour une autre.
REQUIRED_IF = [
    [
        "action",
        "reset_field",
        ["field"],
    ],
    [
        "action",
        "revert_to_snapshot",
        ["snapshot_id"],
    ],
    [
        "action",
        "scale",
        ["gadget_type"],
    ],
]

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(exoscale_argument_spec())
ARGUMENT_SPEC.update(exoscale_waitable_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = ActionModule(
    resource="gadget",
    selector="id",
    actions=(
        Action(
            name="reset_field",
            operation=Operation(
                id="reset-gadget-field",
                method="reset_gadget_field",
                path_params={"id": "id", "field": "field"},
                is_async=True,
            ),
        ),
        Action(
            name="revert_to_snapshot",
            operation=Operation(
                id="revert-gadget-to-snapshot",
                method="revert_gadget_to_snapshot",
                path_params={"id": "gadget-id"},
                body_params={"snapshot_id": "id"},
                is_async=True,
            ),
        ),
        Action(
            name="scale",
            operation=Operation(
                id="scale-gadget",
                method="scale_gadget",
                path_params={"id": "id"},
                body_params={"gadget_type": "gadget-type"},
                is_async=True,
            ),
        ),
        Action(
            name="start",
            operation=Operation(
                id="start-gadget",
                method="start_gadget",
                path_params={"id": "id"},
                body_params={"rescue_profile": "rescue-profile"},
                is_async=True,
            ),
        ),
    ),
)


def main() -> None:
    module = AnsibleModule(
        argument_spec=ARGUMENT_SPEC, required_if=REQUIRED_IF, supports_check_mode=True
    )
    run_action_module(module, MODULE)


if __name__ == "__main__":
    main()
