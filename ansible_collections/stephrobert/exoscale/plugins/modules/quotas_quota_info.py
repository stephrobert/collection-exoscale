#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/exoscale/exoscale.v2.json
# Opérations : get-quota, list-quotas
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: quotas_quota_info
short_description: Gather information about Exoscale quotas
version_added: 0.1.0
description:
- Read one Exoscale quota by its identifier, or list them. This module never changes anything.
author:
- Stéphane Robert (@stephrobert)
options:
  entity:
    description: Not documented by the Exoscale API contract.
    type: str
extends_documentation_fragment:
- stephrobert.exoscale.exoscale
"""

EXAMPLES = r"""
- name: List quotas
  stephrobert.exoscale.quotas_quota_info:
    zone: ch-gva-2
  register: result
- name: Read one quota
  stephrobert.exoscale.quotas_quota_info:
    zone: ch-gva-2
    entity: 11111111-2222-3333-4444-555555555555
  register: result
"""

RETURN = r"""
quota:
  description: The quota, when a selector is given.
  returned: when the selector is given
  type: dict
quotas:
  description: The quotas.
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
    "entity": {"type": "str"},
}

#: Ce que le contrat exige pour une action et pas pour une autre.
REQUIRED_IF = []

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(exoscale_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = InfoModule(
    resource="quota",
    get_operation=Operation(
        id="get-quota",
        method="get_quota",
        path_params={"entity": "entity"},
    ),
    list_operation=Operation(
        id="list-quotas",
        method="list_quotas",
        path_params={},
        payload_field="quotas",
        is_list=True,
    ),
    selector="entity",
)


def main() -> None:
    module = AnsibleModule(
        argument_spec=ARGUMENT_SPEC, required_if=REQUIRED_IF, supports_check_mode=True
    )
    run_info_module(module, MODULE)


if __name__ == "__main__":
    main()
