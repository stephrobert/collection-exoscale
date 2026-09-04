#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/exoscale/exoscale.v2.json
# Opérations : get-dbaas-external-integration, list-dbaas-external-integrations
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: dbaas_external_integration_info
short_description: Gather information about Exoscale dbaas external integrations
version_added: 0.1.0
description:
- Read one Exoscale dbaas external integration by its identifier, or list them. This module
  never changes anything.
author:
- Stéphane Robert (@stephrobert)
options:
  integration_id:
    description: Not documented by the Exoscale API contract.
    type: str
  service_name:
    description: Not documented by the Exoscale API contract.
    type: str
    required: true
extends_documentation_fragment:
- stephrobert.exoscale.exoscale
"""

EXAMPLES = r"""
- name: List dbaas external integrations
  stephrobert.exoscale.dbaas_external_integration_info:
    zone: ch-gva-2
  register: result
- name: Read one dbaas external integration
  stephrobert.exoscale.dbaas_external_integration_info:
    zone: ch-gva-2
    integration_id: 11111111-2222-3333-4444-555555555555
  register: result
"""

RETURN = r"""
dbaas_external_integration:
  description: The dbaas external integration, when a selector is given.
  returned: when the selector is given
  type: dict
dbaas_external_integrations:
  description: The dbaas external integrations.
  returned: when no selector is given
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
    "integration_id": {"type": "str"},
    "service_name": {"type": "str", "required": True},
}

#: Ce que le contrat exige pour une action et pas pour une autre.
REQUIRED_IF = []

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(exoscale_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = InfoModule(
    resource="dbaas_external_integration",
    get_operation=Operation(
        id="get-dbaas-external-integration",
        method="get_dbaas_external_integration",
        path_params={"integration_id": "integration-id"},
    ),
    list_operation=Operation(
        id="list-dbaas-external-integrations",
        method="list_dbaas_external_integrations",
        path_params={"service_name": "service-name"},
        payload_field="external-integrations",
        is_list=True,
    ),
    selector="integration_id",
)


def main() -> None:
    module = AnsibleModule(
        argument_spec=ARGUMENT_SPEC, required_if=REQUIRED_IF, supports_check_mode=True
    )
    run_info_module(module, MODULE)


if __name__ == "__main__":
    main()
