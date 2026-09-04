#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/exoscale/exoscale.v2.json
# Opérations : reset-dbaas-grafana-user-password
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: dbaas_grafana_password_action
short_description: Perform an action on an Exoscale dbaas grafana password
version_added: 0.1.0
description:
- 'Trigger one of the following actions on an existing dbaas grafana password: C(reset_dbaas_grafana_user_password).'
author:
- Stéphane Robert (@stephrobert)
options:
  action:
    description: The action to trigger on the dbaas grafana password.
    type: str
    required: true
    choices:
    - reset_dbaas_grafana_user_password
  service_name:
    description: Not documented by the Exoscale API contract.
    type: str
    required: true
  username:
    description: Not documented by the Exoscale API contract.
    type: str
    required: true
  password:
    description: New password
    type: str
extends_documentation_fragment:
- stephrobert.exoscale.exoscale
- stephrobert.exoscale.exoscale.wait
notes:
- 'Every action is asynchronous on the Exoscale API: the module waits for the returned operation
  to reach C(success) when I(wait) is true, and returns the operation as accepted otherwise.'
"""

EXAMPLES = r"""
- name: Run reset_dbaas_grafana_user_password on a dbaas grafana password
  stephrobert.exoscale.dbaas_grafana_password_action:
    zone: ch-gva-2
    action: reset_dbaas_grafana_user_password
    service_name: 11111111-2222-3333-4444-555555555555
    username: 11111111-2222-3333-4444-555555555555
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
        "choices": ["reset_dbaas_grafana_user_password"],
    },
    "service_name": {"type": "str", "required": True},
    "username": {"type": "str", "required": True},
    "password": {"type": "str", "no_log": True},
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
    resource="dbaas_grafana_password",
    selector=None,
    actions=(
        Action(
            name="reset_dbaas_grafana_user_password",
            operation=Operation(
                id="reset-dbaas-grafana-user-password",
                method="reset_dbaas_grafana_user_password",
                path_params={"service_name": "service-name", "username": "username"},
                body_params={"password": "password"},
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
