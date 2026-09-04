#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/exoscale/exoscale.v2.json
# Opérations : evict-sks-nodepool-members, scale-sks-nodepool
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: sks_cluster_nodepool_action
short_description: Perform an action on an Exoscale sks cluster nodepool
version_added: 0.1.0
description:
- 'Trigger one of the following actions on an existing sks cluster nodepool: C(evict_sks_nodepool_members),
  C(scale_sks_nodepool).'
author:
- Stéphane Robert (@stephrobert)
options:
  action:
    description: The action to trigger on the sks cluster nodepool.
    type: str
    required: true
    choices:
    - evict_sks_nodepool_members
    - scale_sks_nodepool
  id:
    description: Not documented by the Exoscale API contract.
    type: str
    required: true
  sks_nodepool_id:
    description: Not documented by the Exoscale API contract.
    type: str
    required: true
  instances:
    description: Not documented by the Exoscale API contract.
    type: list
    elements: str
  size:
    description: Number of instances
    type: int
extends_documentation_fragment:
- stephrobert.exoscale.exoscale
- stephrobert.exoscale.exoscale.wait
notes:
- 'Every action is asynchronous on the Exoscale API: the module waits for the returned operation
  to reach C(success) when I(wait) is true, and returns the operation as accepted otherwise.'
"""

EXAMPLES = r"""
- name: Run evict_sks_nodepool_members on a sks cluster nodepool
  stephrobert.exoscale.sks_cluster_nodepool_action:
    zone: ch-gva-2
    action: evict_sks_nodepool_members
    id: 11111111-2222-3333-4444-555555555555
    sks_nodepool_id: 11111111-2222-3333-4444-555555555555
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
        "choices": ["evict_sks_nodepool_members", "scale_sks_nodepool"],
    },
    "id": {"type": "str", "required": True},
    "sks_nodepool_id": {"type": "str", "required": True},
    "instances": {"type": "list", "elements": "str"},
    "size": {"type": "int"},
}

#: Ce que le contrat exige pour une action et pas pour une autre.
REQUIRED_IF = [
    [
        "action",
        "scale_sks_nodepool",
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
    resource="sks_cluster_nodepool",
    selector=None,
    actions=(
        Action(
            name="evict_sks_nodepool_members",
            operation=Operation(
                id="evict-sks-nodepool-members",
                method="evict_sks_nodepool_members",
                path_params={"id": "id", "sks_nodepool_id": "sks-nodepool-id"},
                body_params={"instances": "instances"},
                is_async=True,
            ),
        ),
        Action(
            name="scale_sks_nodepool",
            operation=Operation(
                id="scale-sks-nodepool",
                method="scale_sks_nodepool",
                path_params={"id": "id", "sks_nodepool_id": "sks-nodepool-id"},
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
