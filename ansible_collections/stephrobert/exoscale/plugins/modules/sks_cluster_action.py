#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/exoscale/exoscale.v2.json
# Opérations : rotate-sks-ccm-credentials, rotate-sks-csi-credentials,
#              rotate-sks-karpenter-credentials, rotate-sks-operators-ca, upgrade-sks-cluster,
#              upgrade-sks-cluster-service-level
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: sks_cluster_action
short_description: Perform an action on an Exoscale sks cluster
version_added: 0.1.0
description:
- 'Trigger one of the following actions on an existing sks cluster: C(rotate_sks_ccm_credentials),
  C(rotate_sks_csi_credentials), C(rotate_sks_karpenter_credentials), C(rotate_sks_operators_ca),
  C(upgrade), C(upgrade_service_level).'
author:
- Stéphane Robert (@stephrobert)
options:
  action:
    description: The action to trigger on the sks cluster.
    type: str
    required: true
    choices:
    - rotate_sks_ccm_credentials
    - rotate_sks_csi_credentials
    - rotate_sks_karpenter_credentials
    - rotate_sks_operators_ca
    - upgrade
    - upgrade_service_level
  id:
    description: Not documented by the Exoscale API contract.
    type: str
    required: true
  version:
    description: Control plane Kubernetes version
    type: str
extends_documentation_fragment:
- stephrobert.exoscale.exoscale
- stephrobert.exoscale.exoscale.wait
notes:
- 'Every action is asynchronous on the Exoscale API: the module waits for the returned operation
  to reach C(success) when I(wait) is true, and returns the operation as accepted otherwise.'
"""

EXAMPLES = r"""
- name: Run rotate_sks_ccm_credentials on a sks cluster
  stephrobert.exoscale.sks_cluster_action:
    zone: ch-gva-2
    action: rotate_sks_ccm_credentials
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
        "choices": [
            "rotate_sks_ccm_credentials",
            "rotate_sks_csi_credentials",
            "rotate_sks_karpenter_credentials",
            "rotate_sks_operators_ca",
            "upgrade",
            "upgrade_service_level",
        ],
    },
    "id": {"type": "str", "required": True},
    "version": {"type": "str"},
}

#: Ce que le contrat exige pour une action et pas pour une autre.
REQUIRED_IF = [
    [
        "action",
        "upgrade",
        ["version"],
    ],
]

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(exoscale_argument_spec())
ARGUMENT_SPEC.update(exoscale_waitable_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = ActionModule(
    resource="sks_cluster",
    selector="id",
    actions=(
        Action(
            name="rotate_sks_ccm_credentials",
            operation=Operation(
                id="rotate-sks-ccm-credentials",
                method="rotate_sks_ccm_credentials",
                path_params={"id": "id"},
                is_async=True,
            ),
        ),
        Action(
            name="rotate_sks_csi_credentials",
            operation=Operation(
                id="rotate-sks-csi-credentials",
                method="rotate_sks_csi_credentials",
                path_params={"id": "id"},
                is_async=True,
            ),
        ),
        Action(
            name="rotate_sks_karpenter_credentials",
            operation=Operation(
                id="rotate-sks-karpenter-credentials",
                method="rotate_sks_karpenter_credentials",
                path_params={"id": "id"},
                is_async=True,
            ),
        ),
        Action(
            name="rotate_sks_operators_ca",
            operation=Operation(
                id="rotate-sks-operators-ca",
                method="rotate_sks_operators_ca",
                path_params={"id": "id"},
                is_async=True,
            ),
        ),
        Action(
            name="upgrade",
            operation=Operation(
                id="upgrade-sks-cluster",
                method="upgrade_sks_cluster",
                path_params={"id": "id"},
                body_params={"version": "version"},
                is_async=True,
            ),
        ),
        Action(
            name="upgrade_service_level",
            operation=Operation(
                id="upgrade-sks-cluster-service-level",
                method="upgrade_sks_cluster_service_level",
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
