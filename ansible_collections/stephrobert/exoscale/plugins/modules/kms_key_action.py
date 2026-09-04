#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/exoscale/exoscale.v2.json
# Opérations : disable-kms-key, disable-kms-key-rotation, enable-kms-key, enable-kms-key-rotation,
#              replicate-kms-key, rotate-kms-key
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: kms_key_action
short_description: Perform an action on an Exoscale kms key
version_added: 0.1.0
description:
- 'Trigger one of the following actions on an existing kms key: C(disable), C(disable_rotation),
  C(enable), C(enable_rotation), C(replicate), C(rotate).'
author:
- Stéphane Robert (@stephrobert)
options:
  action:
    description: The action to trigger on the kms key.
    type: str
    required: true
    choices:
    - disable
    - disable_rotation
    - enable
    - enable_rotation
    - replicate
    - rotate
  id:
    description: Not documented by the Exoscale API contract.
    type: str
    required: true
  rotation_period:
    description: The number of days between each automatic key rotation.
    type: int
    default: 365
extends_documentation_fragment:
- stephrobert.exoscale.exoscale
notes:
- 'Every action of this module answers at once: the API response is returned under RV(result),
  and there is nothing to wait for.'
"""

EXAMPLES = r"""
- name: Run disable on a kms key
  stephrobert.exoscale.kms_key_action:
    zone: ch-gva-2
    action: disable
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
        "choices": [
            "disable",
            "disable_rotation",
            "enable",
            "enable_rotation",
            "replicate",
            "rotate",
        ],
    },
    "id": {"type": "str", "required": True},
    "rotation_period": {"type": "int", "default": 365},
}

#: Ce que le contrat exige pour une action et pas pour une autre.
REQUIRED_IF = []

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(exoscale_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = ActionModule(
    resource="kms_key",
    selector="id",
    actions=(
        Action(
            name="disable",
            operation=Operation(
                id="disable-kms-key",
                method="disable_kms_key",
                path_params={"id": "id"},
            ),
        ),
        Action(
            name="disable_rotation",
            operation=Operation(
                id="disable-kms-key-rotation",
                method="disable_kms_key_rotation",
                path_params={"id": "id"},
            ),
        ),
        Action(
            name="enable",
            operation=Operation(
                id="enable-kms-key",
                method="enable_kms_key",
                path_params={"id": "id"},
            ),
        ),
        Action(
            name="enable_rotation",
            operation=Operation(
                id="enable-kms-key-rotation",
                method="enable_kms_key_rotation",
                path_params={"id": "id"},
                body_params={"rotation_period": "rotation-period"},
            ),
        ),
        Action(
            name="replicate",
            operation=Operation(
                id="replicate-kms-key",
                method="replicate_kms_key",
                path_params={"id": "id"},
                body_params={"zone": "zone"},
            ),
        ),
        Action(
            name="rotate",
            operation=Operation(
                id="rotate-kms-key",
                method="rotate_kms_key",
                path_params={"id": "id"},
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
