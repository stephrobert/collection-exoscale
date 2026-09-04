#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Contrat de laboratoire (@lab)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : tests/fixtures/gadget/input/exoscale.v2.json
# Opérations : get-usage-report
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: gadget_usage_report_info
short_description: Gather information about Exoscale usage reports
version_added: 9.9.9
description:
- Read one Exoscale usage report. This module never changes anything.
author:
- Contrat de laboratoire (@lab)
options:
  period:
    description: Not documented by the Exoscale API contract.
    type: str
extends_documentation_fragment:
- lab.gadget.exoscale
"""

EXAMPLES = r"""
- name: Read one usage report
  lab.gadget.gadget_usage_report_info:
    zone: ch-gva-2
  register: result
"""

RETURN = r"""
usage_report:
  description: The usage report.
  returned: always
  type: dict
"""

from ansible.module_utils.basic import AnsibleModule  # noqa: E402

from ansible_collections.lab.gadget.plugins.module_utils.exoscale import (  # noqa: E402
    InfoModule,
    Operation,
    exoscale_argument_spec,
    run_info_module,
)

#: Options propres au module, traduites depuis le contrat.
MODULE_ARGUMENT_SPEC = {
    "period": {"type": "str"},
}

#: Ce que le contrat exige pour une action et pas pour une autre.
REQUIRED_IF = []

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(exoscale_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = InfoModule(
    resource="usage_report",
    get_operation=Operation(
        id="get-usage-report",
        method="get_usage_report",
        path_params={},
        body_params={"period": "period"},
    ),
)


def main() -> None:
    module = AnsibleModule(
        argument_spec=ARGUMENT_SPEC, required_if=REQUIRED_IF, supports_check_mode=True
    )
    run_info_module(module, MODULE)


if __name__ == "__main__":
    main()
