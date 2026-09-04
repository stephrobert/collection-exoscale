#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/exoscale/exoscale.v2.json
# Opérations : get-env-impact
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: organization_env_impact_info
short_description: Gather information about Exoscale env impacts
version_added: 0.1.0
description:
- Read one Exoscale env impact. This module never changes anything.
author:
- Stéphane Robert (@stephrobert)
options:
  period:
    description: Not documented by the Exoscale API contract.
    type: str
    required: true
extends_documentation_fragment:
- stephrobert.exoscale.exoscale
"""

EXAMPLES = r"""
- name: Read one env impact
  stephrobert.exoscale.organization_env_impact_info:
    zone: ch-gva-2
    period: 11111111-2222-3333-4444-555555555555
  register: result
"""

RETURN = r"""
env_impact:
  description: The env impact.
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
    "period": {"type": "str", "required": True},
}

#: Ce que le contrat exige pour une action et pas pour une autre.
REQUIRED_IF = []

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(exoscale_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = InfoModule(
    resource="env_impact",
    get_operation=Operation(
        id="get-env-impact",
        method="get_env_impact",
        path_params={"period": "period"},
    ),
)


def main() -> None:
    module = AnsibleModule(
        argument_spec=ARGUMENT_SPEC, required_if=REQUIRED_IF, supports_check_mode=True
    )
    run_info_module(module, MODULE)


if __name__ == "__main__":
    main()
