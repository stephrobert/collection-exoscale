#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/exoscale/exoscale.v2.json
# Opérations : reset-instance-pool-field, scale-instance-pool
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: compute_instance_pool_action
short_description: Perform an action on an Exoscale instance pool
version_added: 0.1.0
description:
- 'Trigger one of the following actions on an existing instance pool: C(reset_field), C(scale).'
author:
- Stéphane Robert (@stephrobert)
options:
  action:
    description: The action to trigger on the instance pool.
    type: str
    required: true
    choices:
    - reset_field
    - scale
  id:
    description: Not documented by the Exoscale API contract.
    type: str
    required: true
  field:
    description: Not documented by the Exoscale API contract.
    type: str
    choices:
    - anti-affinity-groups
    - description
    - labels
    - security-groups
    - elastic-ips
    - private-networks
    - ssh-key
    - user-data
    - deploy-target
    - ipv6-enabled
  size:
    description: Number of managed Instances
    type: int
extends_documentation_fragment:
- stephrobert.exoscale.exoscale
- stephrobert.exoscale.exoscale.wait
notes:
- 'Every action is asynchronous on the Exoscale API: the module waits for the returned operation
  to reach C(success) when I(wait) is true, and returns the operation as accepted otherwise.'
"""

EXAMPLES = r"""
- name: Run reset_field on a instance pool
  stephrobert.exoscale.compute_instance_pool_action:
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
        "choices": ["reset_field", "scale"],
    },
    "id": {"type": "str", "required": True},
    "field": {
        "type": "str",
        "choices": [
            "anti-affinity-groups",
            "description",
            "labels",
            "security-groups",
            "elastic-ips",
            "private-networks",
            "ssh-key",
            "user-data",
            "deploy-target",
            "ipv6-enabled",
        ],
    },
    "size": {"type": "int"},
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
        "scale",
        ["size"],
    ],
]

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(exoscale_argument_spec())
ARGUMENT_SPEC.update(exoscale_waitable_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = ActionModule(
    resource="instance_pool",
    selector="id",
    actions=(
        Action(
            name="reset_field",
            operation=Operation(
                id="reset-instance-pool-field",
                method="reset_instance_pool_field",
                path_params={"id": "id", "field": "field"},
                is_async=True,
            ),
        ),
        Action(
            name="scale",
            operation=Operation(
                id="scale-instance-pool",
                method="scale_instance_pool",
                path_params={"id": "id"},
                body_params={"size": "size"},
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
