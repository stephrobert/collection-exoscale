#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Contrat de laboratoire (@lab)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : tests/fixtures/gadget/input/exoscale.v2.json
# Opérations : reveal-gadget-password
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: gadget_gadget_password_info
short_description: Gather information about Exoscale gadget passwords
version_added: 9.9.9
description:
- Read one Exoscale gadget password by its identifier, or list them. This module never changes
  anything.
author:
- Contrat de laboratoire (@lab)
options:
  id:
    description: Not documented by the Exoscale API contract.
    type: str
extends_documentation_fragment:
- lab.gadget.exoscale
notes:
- 'The returned value is a secret: do not log the task output.'
"""

EXAMPLES = r"""
- name: Read one gadget password
  lab.gadget.gadget_gadget_password_info:
    zone: ch-gva-2
    id: 11111111-2222-3333-4444-555555555555
  register: result
"""

RETURN = r"""
gadget_password:
  description: The gadget password, when a selector is given.
  returned: when the selector is given
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
    "id": {"type": "str"},
}

#: Ce que le contrat exige pour une action et pas pour une autre.
REQUIRED_IF = []

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(exoscale_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = InfoModule(
    resource="gadget_password",
    get_operation=Operation(
        id="reveal-gadget-password",
        method="reveal_gadget_password",
        path_params={"id": "id"},
    ),
    selector="id",
)


def main() -> None:
    module = AnsibleModule(
        argument_spec=ARGUMENT_SPEC, required_if=REQUIRED_IF, supports_check_mode=True
    )
    run_info_module(module, MODULE)


if __name__ == "__main__":
    main()
