#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/exoscale/exoscale.v2.json
# Opérations : reveal-dbaas-postgres-user-password
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: dbaas_postgres_password_info
short_description: Gather information about Exoscale dbaas postgres passwords
version_added: 0.1.0
description:
- Read one Exoscale dbaas postgres password. This module never changes anything.
author:
- Stéphane Robert (@stephrobert)
options:
  service_name:
    description: Not documented by the Exoscale API contract.
    type: str
    required: true
  username:
    description: Not documented by the Exoscale API contract.
    type: str
    required: true
extends_documentation_fragment:
- stephrobert.exoscale.exoscale
notes:
- 'The returned value is a secret: do not log the task output.'
"""

EXAMPLES = r"""
- name: Read one dbaas postgres password
  stephrobert.exoscale.dbaas_postgres_password_info:
    zone: ch-gva-2
    service_name: 11111111-2222-3333-4444-555555555555
    username: 11111111-2222-3333-4444-555555555555
  register: result
"""

RETURN = r"""
dbaas_postgres_password:
  description: The dbaas postgres password.
  returned: always
  type: dict
"""

from ansible.module_utils.basic import AnsibleModule  # noqa: E402

from ansible_collections.stephrobert.exoscale.plugins.module_utils.exoscale import (  # noqa: E402
    InfoModule,
    Operation,
    exoscale_argument_spec,
    run_info_module,
)

#: Options propres au module, traduites depuis le contrat.
MODULE_ARGUMENT_SPEC = {
    "service_name": {"type": "str", "required": True},
    "username": {"type": "str", "required": True},
}

#: Ce que le contrat exige pour une action et pas pour une autre.
REQUIRED_IF = []

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(exoscale_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = InfoModule(
    resource="dbaas_postgres_password",
    get_operation=Operation(
        id="reveal-dbaas-postgres-user-password",
        method="reveal_dbaas_postgres_user_password",
        path_params={"service_name": "service-name", "username": "username"},
    ),
)


def main() -> None:
    module = AnsibleModule(
        argument_spec=ARGUMENT_SPEC, required_if=REQUIRED_IF, supports_check_mode=True
    )
    run_info_module(module, MODULE)


if __name__ == "__main__":
    main()
