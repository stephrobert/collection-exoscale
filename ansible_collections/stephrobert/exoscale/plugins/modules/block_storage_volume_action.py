#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/exoscale/exoscale.v2.json
# Opérations : resize-block-storage-volume
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: block_storage_volume_action
short_description: Perform an action on an Exoscale block storage volume
version_added: 0.1.0
description:
- 'Trigger one of the following actions on an existing block storage volume: C(resize).'
author:
- Stéphane Robert (@stephrobert)
options:
  action:
    description: The action to trigger on the block storage volume.
    type: str
    required: true
    choices:
    - resize
  id:
    description: Not documented by the Exoscale API contract.
    type: str
    required: true
  size:
    description: Volume size in GiB
    type: int
extends_documentation_fragment:
- stephrobert.exoscale.exoscale
notes:
- 'Every action of this module answers at once: the API response is returned under RV(result),
  and there is nothing to wait for.'
"""

EXAMPLES = r"""
- name: Run resize on a block storage volume
  stephrobert.exoscale.block_storage_volume_action:
    zone: ch-gva-2
    action: resize
    id: 11111111-2222-3333-4444-555555555555
"""

RETURN = r"""
result:
  description: The API response of an action that answers at once, with its result rather
    than with an operation to wait for.
  returned: always
  type: dict
"""

from ansible.module_utils.basic import AnsibleModule  # noqa: E402

from ansible_collections.stephrobert.exoscale.plugins.module_utils.exoscale import (  # noqa: E402
    Action,
    ActionModule,
    Operation,
    exoscale_argument_spec,
    run_action_module,
)

#: Options propres au module, traduites depuis le contrat.
MODULE_ARGUMENT_SPEC = {
    "action": {
        "type": "str",
        "required": True,
        "choices": ["resize"],
    },
    "id": {"type": "str", "required": True},
    "size": {"type": "int"},
}

#: Ce que le contrat exige pour une action et pas pour une autre.
REQUIRED_IF = [
    [
        "action",
        "resize",
        ["size"],
    ],
]

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(exoscale_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = ActionModule(
    resource="block_storage_volume",
    selector="id",
    actions=(
        Action(
            name="resize",
            operation=Operation(
                id="resize-block-storage-volume",
                method="resize_block_storage_volume",
                path_params={"id": "id"},
                body_params={"size": "size"},
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
