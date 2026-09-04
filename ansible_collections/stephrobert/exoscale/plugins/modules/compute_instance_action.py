#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/exoscale/exoscale.v2.json
# Opérations : add-instance-protection, enable-tpm, reboot-instance, remove-instance-protection,
#              reset-instance-field, reset-instance-password, resize-instance-disk,
#              revert-instance-to-snapshot, scale-instance, start-instance, stop-instance
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: compute_instance_action
short_description: Perform an action on an Exoscale instance
version_added: 0.1.0
description:
- 'Trigger one of the following actions on an existing instance: C(add_protection), C(enable_tpm),
  C(reboot), C(remove_protection), C(reset_field), C(reset_password), C(resize_disk), C(revert_to_snapshot),
  C(scale), C(start), C(stop).'
author:
- Stéphane Robert (@stephrobert)
options:
  action:
    description: The action to trigger on the instance.
    type: str
    required: true
    choices:
    - add_protection
    - enable_tpm
    - reboot
    - remove_protection
    - reset_field
    - reset_password
    - resize_disk
    - revert_to_snapshot
    - scale
    - start
    - stop
  id:
    description: Not documented by the Exoscale API contract.
    type: str
    required: true
  field:
    description: Not documented by the Exoscale API contract.
    type: str
    choices:
    - labels
  disk_size:
    description: Instance disk size in GiB
    type: int
  snapshot_id:
    description: Snapshot ID
    type: str
  instance_type:
    description: Instance Type
    type: dict
  rescue_profile:
    description: 'Boot in Rescue Mode, using named profile (supported: netboot, netboot-efi)'
    type: str
    choices:
    - netboot-efi
    - netboot
extends_documentation_fragment:
- stephrobert.exoscale.exoscale
- stephrobert.exoscale.exoscale.wait
notes:
- 'Every action is asynchronous on the Exoscale API: the module waits for the returned operation
  to reach C(success) when I(wait) is true, and returns the operation as accepted otherwise.'
- Once the operation succeeds, the module reads the instance until its C(state) reaches the
  expected value (C(reboot) leads to C(running), C(start) leads to C(running), C(stop) leads
  to C(stopped)), and reports C(changed=false) without sending anything when the instance
  already is in that state, except for C(reboot), which always acts.
"""

EXAMPLES = r"""
- name: Run add_protection on a instance
  stephrobert.exoscale.compute_instance_action:
    zone: ch-gva-2
    action: add_protection
    id: 11111111-2222-3333-4444-555555555555
"""

RETURN = r"""
operation:
  description: 'The Exoscale operation object: its C(state) is C(success) once the work is
    done, C(pending) when the module did not wait.'
  returned: always
  type: dict
state:
  description: The C(state) of the instance, read after the operation.
  returned: when an expected state is declared for the action
  type: str
"""

from ansible.module_utils.basic import AnsibleModule  # noqa: E402

from ansible_collections.stephrobert.exoscale.plugins.module_utils.exoscale import (  # noqa: E402
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
        "choices": [
            "add_protection",
            "enable_tpm",
            "reboot",
            "remove_protection",
            "reset_field",
            "reset_password",
            "resize_disk",
            "revert_to_snapshot",
            "scale",
            "start",
            "stop",
        ],
    },
    "id": {"type": "str", "required": True},
    "field": {
        "type": "str",
        "choices": ["labels"],
    },
    "disk_size": {"type": "int"},
    "snapshot_id": {"type": "str"},
    "instance_type": {"type": "dict"},
    "rescue_profile": {
        "type": "str",
        "choices": ["netboot-efi", "netboot"],
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
        "resize_disk",
        ["disk_size"],
    ],
    [
        "action",
        "revert_to_snapshot",
        ["snapshot_id"],
    ],
    [
        "action",
        "scale",
        ["instance_type"],
    ],
]

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(exoscale_argument_spec())
ARGUMENT_SPEC.update(exoscale_waitable_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = ActionModule(
    resource="instance",
    selector="id",
    actions=(
        Action(
            name="add_protection",
            operation=Operation(
                id="add-instance-protection",
                method="add_instance_protection",
                path_params={"id": "id"},
                is_async=True,
            ),
        ),
        Action(
            name="enable_tpm",
            operation=Operation(
                id="enable-tpm",
                method="enable_tpm",
                path_params={"id": "id"},
                is_async=True,
            ),
        ),
        Action(
            name="reboot",
            operation=Operation(
                id="reboot-instance",
                method="reboot_instance",
                path_params={"id": "id"},
                is_async=True,
            ),
            expected_state="running",
            always=True,
        ),
        Action(
            name="remove_protection",
            operation=Operation(
                id="remove-instance-protection",
                method="remove_instance_protection",
                path_params={"id": "id"},
                is_async=True,
            ),
        ),
        Action(
            name="reset_field",
            operation=Operation(
                id="reset-instance-field",
                method="reset_instance_field",
                path_params={"id": "id", "field": "field"},
                is_async=True,
            ),
        ),
        Action(
            name="reset_password",
            operation=Operation(
                id="reset-instance-password",
                method="reset_instance_password",
                path_params={"id": "id"},
                is_async=True,
            ),
        ),
        Action(
            name="resize_disk",
            operation=Operation(
                id="resize-instance-disk",
                method="resize_instance_disk",
                path_params={"id": "id"},
                body_params={"disk_size": "disk-size"},
                is_async=True,
            ),
        ),
        Action(
            name="revert_to_snapshot",
            operation=Operation(
                id="revert-instance-to-snapshot",
                method="revert_instance_to_snapshot",
                path_params={"id": "instance-id"},
                body_params={"snapshot_id": "id"},
                is_async=True,
            ),
        ),
        Action(
            name="scale",
            operation=Operation(
                id="scale-instance",
                method="scale_instance",
                path_params={"id": "id"},
                body_params={"instance_type": "instance-type"},
                is_async=True,
            ),
        ),
        Action(
            name="start",
            operation=Operation(
                id="start-instance",
                method="start_instance",
                path_params={"id": "id"},
                body_params={"rescue_profile": "rescue-profile"},
                is_async=True,
            ),
            expected_state="running",
        ),
        Action(
            name="stop",
            operation=Operation(
                id="stop-instance",
                method="stop_instance",
                path_params={"id": "id"},
                is_async=True,
            ),
            expected_state="stopped",
        ),
    ),
    state_field="state",
    read_operation=Operation(
        id="get-instance",
        method="get_instance",
        path_params={"id": "id"},
    ),
)


def main() -> None:
    module = AnsibleModule(
        argument_spec=ARGUMENT_SPEC, required_if=REQUIRED_IF, supports_check_mode=True
    )
    run_action_module(module, MODULE)


if __name__ == "__main__":
    main()
