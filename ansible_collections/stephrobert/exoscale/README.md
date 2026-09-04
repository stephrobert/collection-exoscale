# stephrobert.exoscale

**Day-2** Ansible modules for the Exoscale API v2, produced by the generator
of the repository that hosts this collection:
<https://github.com/stephrobert/collection-exoscale>.

> Terraform provisions resources. Ansible operates existing ones.

Information modules read; action modules trigger an operation on an existing
resource and wait for it to finish. No module creates, deletes or links
resources.

## Installation

```bash
ansible-galaxy collection install stephrobert.exoscale
pip install "exoscale>=0.16"
```

The official Python SDK `exoscale` is the only runtime dependency: it computes
the `EXO2-HMAC-SHA256` request signature and is generated from the same
OpenAPI contract as these modules.

Requires ansible-core 2.17 or later, measured by `ansible-test sanity` on
every version from 2.17 to 2.21.

## Authentication

Every module accepts `api_key`, `api_secret` and `zone`, falling back on the
`EXOSCALE_API_KEY`, `EXOSCALE_API_SECRET` and `EXOSCALE_ZONE` environment
variables. `api_url` (or `EXOSCALE_API_URL`) replaces the host built from the
zone, for a local emulator or a test endpoint.

```yaml
- name: Stop an instance and wait for the operation to succeed
  stephrobert.exoscale.compute_instance_action:
    zone: ch-gva-2
    action: stop
    id: 11111111-2222-3333-4444-555555555555
```

## Asynchronous operations

Every write on the Exoscale API answers with an `operation` object. An action
module waits for that operation to reach `success` when `wait` is true (the
default), fails with the API's reason on `failure` or `timeout`, and returns
the operation as accepted when `wait` is false, with `operation.state` saying
`pending`. A module never reports `changed` for work it did not see finish
unless it says it did not wait.

## Modules

The table below is **derived** from the produced modules, product by
product: each description is the module's own `short_description`, which
comes from the contract. It is rewritten by `mise run readme`, and the CI
fails when it has aged.

<!-- counters:start, produced by scripts/readme_counters.py -->
### compute (26 modules)

Host anything from simple applications to complex architectures.

| module | what it does |
|---|---|
| `compute_anti_affinity_group_info` | Gather information about Exoscale anti affinity groups |
| `compute_deploy_target_info` | Gather information about Exoscale deploy targets |
| `compute_elastic_ip_action` | Perform an action on an Exoscale elastic ip |
| `compute_elastic_ip_info` | Gather information about Exoscale elastic ips |
| `compute_instance_action` | Perform an action on an Exoscale instance |
| `compute_instance_console_info` | Gather information about Exoscale instance consoles |
| `compute_instance_info` | Gather information about Exoscale instances |
| `compute_instance_password_info` | Gather information about Exoscale instance passwords |
| `compute_instance_pool_action` | Perform an action on an Exoscale instance pool |
| `compute_instance_pool_info` | Gather information about Exoscale instance pools |
| `compute_instance_type_info` | Gather information about Exoscale instance types |
| `compute_load_balancer_action` | Perform an action on an Exoscale load balancer |
| `compute_load_balancer_info` | Gather information about Exoscale load balancers |
| `compute_private_network_action` | Perform an action on an Exoscale private network |
| `compute_private_network_info` | Gather information about Exoscale private networks |
| `compute_reverse_dns_elastic_ip_info` | Gather information about Exoscale reverse dns elastic ips |
| `compute_reverse_dns_instance_info` | Gather information about Exoscale reverse dns instances |
| `compute_security_group_info` | Gather information about Exoscale security groups |
| `compute_snapshot_action` | Perform an action on an Exoscale snapshot |
| `compute_snapshot_info` | Gather information about Exoscale snapshots |
| `compute_ssh_key_info` | Gather information about Exoscale ssh keys |
| `compute_template_info` | Gather information about Exoscale templates |
| `compute_vpc_info` | Gather information about Exoscale vpcs |
| `compute_vpc_route_info` | Gather information about Exoscale vpc routes |
| `compute_vpc_subnet_info` | Gather information about Exoscale vpc subnets |
| `compute_vpc_subnet_route_info` | Gather information about Exoscale vpc subnet routes |
<!-- counters:end -->

## State

The modules import, their `argument_spec` is accepted by Ansible, the
installed SDK exposes every method they call, and `ansible-test sanity`
passes. They have not been played against the real cloud yet.

## Where to report a defect

This collection is generated. A defect in a module is not fixed in the
module, which the next generation rewrites: it belongs to the contract, to a
classification rule or to an override, in the repository linked above.
