#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Contrat de laboratoire (@lab)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : tests/fixtures/gadget/input/exoscale.v2.json
# Opérations : start-gadget-maintenance
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: gadget_maintenance_action
short_description: Perform an action on an Exoscale gadget maintenance
version_added: 9.9.9
description:
- 'Trigger one of the following actions on an existing gadget maintenance: C(start).'
author:
- Contrat de laboratoire (@lab)
options:
  action:
    description: The action to trigger on the gadget maintenance.
    type: str
    required: true
    choices:
    - start
  id:
    description: Not documented by the Exoscale API contract.
    type: str
    required: true
extends_documentation_fragment:
- lab.gadget.exoscale
- lab.gadget.exoscale.wait
notes:
- 'Every action is asynchronous on the Exoscale API: the module waits for the returned operation
  to reach C(success) when I(wait) is true, and returns the operation as accepted otherwise.'
"""

EXAMPLES = r"""
- name: Run start on a gadget maintenance
  lab.gadget.gadget_maintenance_action:
    zone: ch-gva-2
    action: start
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
        "choices": ["start"],
    },
    "id": {"type": "str", "required": True},
}

#: Ce que le contrat exige pour une action et pas pour une autre.
REQUIRED_IF = []

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(exoscale_argument_spec())
ARGUMENT_SPEC.update(exoscale_waitable_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = ActionModule(
    resource="gadget_maintenance",
    selector="id",
    actions=(
        Action(
            name="start",
            operation=Operation(
                id="start-gadget-maintenance",
                method="start_gadget_maintenance",
                path_params={"id": "id"},
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
