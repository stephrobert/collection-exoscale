#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/exoscale/exoscale.v2.json
# Opérations : get-deployment-logs
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: ai_log_info
short_description: Gather information about Exoscale ai logs
version_added: 0.1.0
description:
- List Exoscale ai logs. This module never changes anything.
author:
- Stéphane Robert (@stephrobert)
options:
  id:
    description: Not documented by the Exoscale API contract.
    type: str
  stream:
    description: Not documented by the Exoscale API contract.
    type: bool
  tail:
    description: Not documented by the Exoscale API contract.
    type: int
extends_documentation_fragment:
- stephrobert.exoscale.exoscale
"""

EXAMPLES = r"""
- name: List ai logs
  stephrobert.exoscale.ai_log_info:
    zone: ch-gva-2
  register: result
"""

RETURN = r"""
ai_logs:
  description: The ai logs.
  returned: always
  type: list
  elements: dict
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
    "id": {"type": "str"},
    "stream": {"type": "bool"},
    "tail": {"type": "int"},
}

#: Ce que le contrat exige pour une action et pas pour une autre.
REQUIRED_IF = []

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(exoscale_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = InfoModule(
    resource="ai_log",
    list_operation=Operation(
        id="get-deployment-logs",
        method="get_deployment_logs",
        path_params={"id": "id"},
        query_params={"stream": "stream", "tail": "tail"},
        payload_field="logs",
        is_list=True,
    ),
)


def main() -> None:
    module = AnsibleModule(
        argument_spec=ARGUMENT_SPEC, required_if=REQUIRED_IF, supports_check_mode=True
    )
    run_info_module(module, MODULE)


if __name__ == "__main__":
    main()
