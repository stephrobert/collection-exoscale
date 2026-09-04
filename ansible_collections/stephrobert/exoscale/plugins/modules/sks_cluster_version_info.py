#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/exoscale/exoscale.v2.json
# Opérations : list-sks-cluster-versions
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: sks_cluster_version_info
short_description: Gather information about Exoscale sks cluster versions
version_added: 0.1.0
description:
- List Exoscale sks cluster versions. This module never changes anything.
author:
- Stéphane Robert (@stephrobert)
options:
  include_deprecated:
    description: Not documented by the Exoscale API contract.
    type: str
extends_documentation_fragment:
- stephrobert.exoscale.exoscale
"""

EXAMPLES = r"""
- name: List sks cluster versions
  stephrobert.exoscale.sks_cluster_version_info:
    zone: ch-gva-2
  register: result
"""

RETURN = r"""
sks_cluster_versions:
  description: The sks cluster versions.
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
    "include_deprecated": {"type": "str"},
}

#: Ce que le contrat exige pour une action et pas pour une autre.
REQUIRED_IF = []

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(exoscale_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = InfoModule(
    resource="sks_cluster_version",
    list_operation=Operation(
        id="list-sks-cluster-versions",
        method="list_sks_cluster_versions",
        path_params={},
        query_params={"include_deprecated": "include-deprecated"},
        payload_field="sks-cluster-versions",
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
