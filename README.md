# collection-exoscale

A generator of **Day-2** Ansible modules for the Exoscale API v2, and the
`stephrobert.exoscale` collection it produces.

> Terraform provisions resources. Ansible operates existing ones.

The generator therefore produces neither `create` nor `delete`: it produces
information modules and one-shot action modules on existing resources.

## Why this repository exists

No Ansible collection talks to the Exoscale API v2. `ngine_io.exoscale` is
deprecated on Galaxy (last version 1.1.0, 25 August 2023), archived on GitHub
(last commit 21 November 2023), hand-written, and its three modules target v1
APIs closed on 1 May 2024. The `exoscale` namespace exists on Galaxy, and it
is empty.

Exoscale publishes a complete, single OpenAPI 3.0 contract
(`https://openapi-v2.exoscale.com/source.json`): 261 paths, 374 operations,
55 tags. That contract is versioned here, and it is what gets measured rather
than followed by hand.

## State, measured

The block below is **derived**, not written: `scripts/readme_counters.py`
reads the strict report, the generation report, the produced modules, the
test collection, the falsification specs and the CI workflow, and
`mise run readme:check` fails the CI when a number has aged.

<!-- counters:start, produced by scripts/readme_counters.py -->
```text
exoscale v2: 374 operations in a single document, 14 products counted, 14 indexed
  compute v2: 111 operations, 70 asynchronous
    INFO 35 · ACTION 18 · MANAGE 11 · WORKFLOW 0 · LIFECYCLE 34 · IGNORE 13 · UNKNOWN 0
    Day-2 64 · AUTO 64 · OVERRIDE 0 · classified for automatic generation 100.0% (64/64)
  ai v2: 22 operations, 7 asynchronous
    INFO 12 · ACTION 1 · MANAGE 2 · WORKFLOW 0 · LIFECYCLE 6 · IGNORE 1 · UNKNOWN 0
    Day-2 15 · AUTO 15 · OVERRIDE 0 · classified for automatic generation 100.0% (15/15)
  audit_trail v2: 1 operations, 0 asynchronous
    INFO 1 · ACTION 0 · MANAGE 0 · WORKFLOW 0 · LIFECYCLE 0 · IGNORE 0 · UNKNOWN 0
    Day-2 1 · AUTO 1 · OVERRIDE 0 · classified for automatic generation 100.0% (1/1)
  block_storage v2: 13 operations, 8 asynchronous
    INFO 4 · ACTION 1 · MANAGE 2 · WORKFLOW 0 · LIFECYCLE 4 · IGNORE 2 · UNKNOWN 0
    Day-2 7 · AUTO 7 · OVERRIDE 0 · classified for automatic generation 100.0% (7/7)
  ccm v2: 1 operations, 0 asynchronous
    INFO 1 · ACTION 0 · MANAGE 0 · WORKFLOW 0 · LIFECYCLE 0 · IGNORE 0 · UNKNOWN 0
    Day-2 1 · AUTO 1 · OVERRIDE 0 · classified for automatic generation 100.0% (1/1)
  dbaas v2: 146 operations, 90 asynchronous
    INFO 52 · ACTION 19 · MANAGE 19 · WORKFLOW 0 · LIFECYCLE 54 · IGNORE 2 · UNKNOWN 0
    Day-2 90 · AUTO 90 · OVERRIDE 0 · classified for automatic generation 100.0% (90/90)
  dns v2: 10 operations, 5 asynchronous
    INFO 5 · ACTION 0 · MANAGE 1 · WORKFLOW 0 · LIFECYCLE 4 · IGNORE 0 · UNKNOWN 0
    Day-2 6 · AUTO 6 · OVERRIDE 0 · classified for automatic generation 100.0% (6/6)
  general v2: 2 operations, 1 asynchronous
    INFO 2 · ACTION 0 · MANAGE 0 · WORKFLOW 0 · LIFECYCLE 0 · IGNORE 0 · UNKNOWN 0
    Day-2 2 · AUTO 2 · OVERRIDE 0 · classified for automatic generation 100.0% (2/2)
  iam v2: 18 operations, 10 asynchronous
    INFO 6 · ACTION 1 · MANAGE 4 · WORKFLOW 0 · LIFECYCLE 6 · IGNORE 1 · UNKNOWN 0
    Day-2 11 · AUTO 11 · OVERRIDE 0 · classified for automatic generation 100.0% (11/11)
  kms v2: 16 operations, 0 asynchronous
    INFO 3 · ACTION 6 · MANAGE 0 · WORKFLOW 0 · LIFECYCLE 3 · IGNORE 4 · UNKNOWN 0
    Day-2 9 · AUTO 9 · OVERRIDE 0 · classified for automatic generation 100.0% (9/9)
  organization v2: 4 operations, 0 asynchronous
    INFO 4 · ACTION 0 · MANAGE 0 · WORKFLOW 0 · LIFECYCLE 0 · IGNORE 0 · UNKNOWN 0
    Day-2 4 · AUTO 4 · OVERRIDE 0 · classified for automatic generation 100.0% (4/4)
  quotas v2: 2 operations, 0 asynchronous
    INFO 2 · ACTION 0 · MANAGE 0 · WORKFLOW 0 · LIFECYCLE 0 · IGNORE 0 · UNKNOWN 0
    Day-2 2 · AUTO 2 · OVERRIDE 0 · classified for automatic generation 100.0% (2/2)
  sks v2: 25 operations, 14 asynchronous
    INFO 9 · ACTION 8 · MANAGE 2 · WORKFLOW 0 · LIFECYCLE 4 · IGNORE 2 · UNKNOWN 0
    Day-2 19 · AUTO 18 · OVERRIDE 1 · classified for automatic generation 100.0% (19/19)
  sos v2: 2 operations, 0 asynchronous
    INFO 2 · ACTION 0 · MANAGE 0 · WORKFLOW 0 · LIFECYCLE 0 · IGNORE 0 · UNKNOWN 0
    Day-2 2 · AUTO 2 · OVERRIDE 0 · classified for automatic generation 100.0% (2/2)

collection stephrobert.exoscale: 136 modules written, 179 planned, 43 set aside with their reason
  ai_deployment_action                     Perform an action on an Exoscale ai deployment
  ai_deployment_info                       Gather information about Exoscale ai deployments
  ai_inference_engine_parameter_info       Gather information about Exoscale ai inference engine parameters
  ai_instance_type_info                    Gather information about Exoscale ai instance types
  ai_log_info                              Gather information about Exoscale ai logs
  ai_model_info                            Gather information about Exoscale ai models
  ai_quota_info                            Gather information about Exoscale ai quotas
  audit_trail_event_info                   Gather information about Exoscale events
  block_storage_snapshot_info              Gather information about Exoscale block storage snapshots
  block_storage_volume_action              Perform an action on an Exoscale block storage volume
  block_storage_volume_info                Gather information about Exoscale block storage volumes
  ccm_quota_info                           Gather information about Exoscale quotas
  compute_anti_affinity_group_info         Gather information about Exoscale anti affinity groups
  compute_deploy_target_info               Gather information about Exoscale deploy targets
  compute_elastic_ip_action                Perform an action on an Exoscale elastic ip
  compute_elastic_ip_info                  Gather information about Exoscale elastic ips
  compute_instance_action                  Perform an action on an Exoscale instance
  compute_instance_console_info            Gather information about Exoscale instance consoles
  compute_instance_info                    Gather information about Exoscale instances
  compute_instance_password_info           Gather information about Exoscale instance passwords
  compute_instance_pool_action             Perform an action on an Exoscale instance pool
  compute_instance_pool_info               Gather information about Exoscale instance pools
  compute_instance_type_info               Gather information about Exoscale instance types
  compute_load_balancer_action             Perform an action on an Exoscale load balancer
  compute_load_balancer_info               Gather information about Exoscale load balancers
  compute_load_balancer_service_action     Perform an action on an Exoscale load balancer service
  compute_load_balancer_service_info       Gather information about Exoscale load balancer services
  compute_private_network_action           Perform an action on an Exoscale private network
  compute_private_network_info             Gather information about Exoscale private networks
  compute_reverse_dns_elastic_ip_info      Gather information about Exoscale reverse dns elastic ips
  compute_reverse_dns_instance_info        Gather information about Exoscale reverse dns instances
  compute_security_group_info              Gather information about Exoscale security groups
  compute_snapshot_action                  Perform an action on an Exoscale snapshot
  compute_snapshot_info                    Gather information about Exoscale snapshots
  compute_ssh_key_info                     Gather information about Exoscale ssh keys
  compute_template_info                    Gather information about Exoscale templates
  compute_vpc_info                         Gather information about Exoscale vpcs
  compute_vpc_route_info                   Gather information about Exoscale vpc routes
  compute_vpc_subnet_info                  Gather information about Exoscale vpc subnets
  compute_vpc_subnet_route_info            Gather information about Exoscale vpc subnet routes
  dbaas_ca_certificate_info                Gather information about Exoscale dbaas ca certificates
  dbaas_clickhouse_acl_config_info         Gather information about Exoscale dbaas clickhouse acl configs
  dbaas_clickhouse_info                    Gather information about Exoscale dbaas clickhouses
  dbaas_clickhouse_maintenance_action      Perform an action on an Exoscale dbaas clickhouse maintenance
  dbaas_clickhouse_password_action         Perform an action on an Exoscale dbaas clickhouse password
  dbaas_clickhouse_password_info           Gather information about Exoscale dbaas clickhouse passwords
  dbaas_clickhouse_role_info               Gather information about Exoscale dbaas clickhouse roles
  dbaas_clickhouse_user_info               Gather information about Exoscale dbaas clickhouse users
  dbaas_external_endpoint_datadog_info     Gather information about Exoscale dbaas external endpoint datadogs
  dbaas_external_endpoint_elasticsearch_info Gather information about Exoscale dbaas external endpoint elasticsearches
  dbaas_external_endpoint_info             Gather information about Exoscale dbaas external endpoints
  dbaas_external_endpoint_opensearch_info  Gather information about Exoscale dbaas external endpoint opensearches
  dbaas_external_endpoint_prometheus_info  Gather information about Exoscale dbaas external endpoint prometheus
  dbaas_external_endpoint_rsyslog_info     Gather information about Exoscale dbaas external endpoint rsyslogs
  dbaas_external_endpoint_type_info        Gather information about Exoscale dbaas external endpoint types
  dbaas_external_integration_info          Gather information about Exoscale dbaas external integrations
  dbaas_external_integration_settings_datadog_info Gather information about Exoscale dbaas external integration settings datadogs
  dbaas_grafana_info                       Gather information about Exoscale dbaas grafanas
  dbaas_grafana_maintenance_action         Perform an action on an Exoscale dbaas grafana maintenance
  dbaas_grafana_password_action            Perform an action on an Exoscale dbaas grafana password
  dbaas_grafana_password_info              Gather information about Exoscale dbaas grafana passwords
  dbaas_integration_info                   Gather information about Exoscale dbaas integrations
  dbaas_integration_type_info              Gather information about Exoscale dbaas integration types
  dbaas_kafka_acl_config_info              Gather information about Exoscale dbaas kafka acl configs
  dbaas_kafka_info                         Gather information about Exoscale dbaas kafkas
  dbaas_kafka_maintenance_action           Perform an action on an Exoscale dbaas kafka maintenance
  dbaas_kafka_password_action              Perform an action on an Exoscale dbaas kafka password
  dbaas_migration_status_info              Gather information about Exoscale dbaas migration status
  dbaas_mysql_info                         Gather information about Exoscale dbaas mysqls
  dbaas_mysql_maintenance_action           Perform an action on an Exoscale dbaas mysql maintenance
  dbaas_mysql_migration_action             Perform an action on an Exoscale dbaas mysql migration
  dbaas_mysql_password_action              Perform an action on an Exoscale dbaas mysql password
  dbaas_mysql_password_info                Gather information about Exoscale dbaas mysql passwords
  dbaas_mysql_write_action                 Perform an action on an Exoscale dbaas mysql write
  dbaas_opensearch_acl_config_info         Gather information about Exoscale dbaas opensearch acl configs
  dbaas_opensearch_info                    Gather information about Exoscale dbaas opensearches
  dbaas_opensearch_maintenance_action      Perform an action on an Exoscale dbaas opensearch maintenance
  dbaas_opensearch_password_action         Perform an action on an Exoscale dbaas opensearch password
  dbaas_opensearch_password_info           Gather information about Exoscale dbaas opensearch passwords
  dbaas_postgres_info                      Gather information about Exoscale dbaas postgres
  dbaas_postgres_maintenance_action        Perform an action on an Exoscale dbaas postgres maintenance
  dbaas_postgres_migration_action          Perform an action on an Exoscale dbaas postgres migration
  dbaas_postgres_password_action           Perform an action on an Exoscale dbaas postgres password
  dbaas_postgres_password_info             Gather information about Exoscale dbaas postgres passwords
  dbaas_service_info                       Gather information about Exoscale dbaas services
  dbaas_service_log_info                   Gather information about Exoscale dbaas service logs
  dbaas_service_metric_info                Gather information about Exoscale dbaas service metrics
  dbaas_service_type_info                  Gather information about Exoscale dbaas service types
  dbaas_settings_clickhouse_info           Gather information about Exoscale dbaas settings clickhouses
  dbaas_settings_grafana_info              Gather information about Exoscale dbaas settings grafanas
  dbaas_settings_kafka_info                Gather information about Exoscale dbaas settings kafkas
  dbaas_settings_mysql_info                Gather information about Exoscale dbaas settings mysqls
  dbaas_settings_opensearch_info           Gather information about Exoscale dbaas settings opensearches
  dbaas_settings_pg_info                   Gather information about Exoscale dbaas settings pgs
  dbaas_settings_thanos_info               Gather information about Exoscale dbaas settings thanos
  dbaas_settings_valkey_info               Gather information about Exoscale dbaas settings valkeys
  dbaas_task_info                          Gather information about Exoscale dbaas tasks
  dbaas_thanos_info                        Gather information about Exoscale dbaas thanos
  dbaas_thanos_maintenance_action          Perform an action on an Exoscale dbaas thanos maintenance
  dbaas_thanos_password_info               Gather information about Exoscale dbaas thanos passwords
  dbaas_valkey_info                        Gather information about Exoscale dbaas valkeys
  dbaas_valkey_maintenance_action          Perform an action on an Exoscale dbaas valkey maintenance
  dbaas_valkey_migration_action            Perform an action on an Exoscale dbaas valkey migration
  dbaas_valkey_password_action             Perform an action on an Exoscale dbaas valkey password
  dbaas_valkey_password_info               Gather information about Exoscale dbaas valkey passwords
  dbaas_valkey_user_info                   Gather information about Exoscale dbaas valkey users
  dns_domain_info                          Gather information about Exoscale dns domains
  dns_domain_record_info                   Gather information about Exoscale dns domain records
  dns_domain_zone_info                     Gather information about Exoscale dns domain zones
  general_operation_info                   Gather information about Exoscale operations
  general_zone_info                        Gather information about Exoscale zones
  iam_api_key_info                         Gather information about Exoscale api keys
  iam_organization_policy_action           Perform an action on an Exoscale iam organization policy
  iam_organization_policy_info             Gather information about Exoscale iam organization policies
  iam_role_info                            Gather information about Exoscale iam roles
  iam_user_info                            Gather information about Exoscale users
  kms_key_action                           Perform an action on an Exoscale kms key
  kms_key_info                             Gather information about Exoscale kms keys
  kms_key_rotation_info                    Gather information about Exoscale kms key rotations
  organization_env_impact_info             Gather information about Exoscale env impacts
  organization_info                        Gather information about Exoscale organizations
  organization_live_balance_info           Gather information about Exoscale live balances
  organization_usage_report_info           Gather information about Exoscale usage reports
  quotas_quota_info                        Gather information about Exoscale quotas
  sks_cluster_action                       Perform an action on an Exoscale sks cluster
  sks_cluster_cert_info                    Gather information about Exoscale sks cluster certs
  sks_cluster_deprecated_resource_info     Gather information about Exoscale sks cluster deprecated resources
  sks_cluster_info                         Gather information about Exoscale sks clusters
  sks_cluster_inspection_info              Gather information about Exoscale sks cluster inspections
  sks_cluster_kubeconfig_info              Gather information about Exoscale sks cluster kubeconfigs
  sks_cluster_nodepool_action              Perform an action on an Exoscale sks cluster nodepool
  sks_cluster_nodepool_info                Gather information about Exoscale sks cluster nodepools
  sks_cluster_version_info                 Gather information about Exoscale sks cluster versions
  sks_template_info                        Gather information about Exoscale sks templates
  sos_bucket_usage_info                    Gather information about Exoscale sos bucket usages
  sos_presigned_url_info                   Gather information about Exoscale sos presigned urls
  compute (inventory)                      dynamic inventory
  914 unit tests · 40 guards proven by mise run falsify
  CI: 3 jobs, Générateur · collection · Archive
  ansible-test sanity: reported by `mise run sanity`, not counted here
```
<!-- counters:end -->

The modules import, their `argument_spec` is accepted by ansible-core, the
runtime is measured with test doubles, every guard is falsified, the installed
SDK exposes every method a module calls, and `ansible-test sanity` passes on
ansible-core 2.17 to 2.21. **No module has been played against the real cloud
yet.** Saying so is worth more than a green that does not measure it.

## What differs from Scaleway, and why

This repository transposes the architecture of `collection-scaleway`, not its
files. Every gap is measured on the contract; the full table is in
`CLAUDE.md`. The three most structuring:

* **one document for every product.** `specs/exoscale/products.txt` indexes
  root tags, and `generator/source/` splits the document by tag family;
  `python -m generator products` counts what is not indexed, so that nothing
  disappears in silence;
* **actions are carried by PUT, and `reset-*-field` by DELETE.** Scaleway's
  rules leave 58 UNKNOWN out of 374 operations; Exoscale's leave 0;
* **203 writes out of 374 answer with an asynchronous `operation`.** A module
  that reports `changed` without waiting lies: the runtime waits for the
  operation to reach `success` when `wait` is true, and returns it in every
  case.

## Commands

```bash
mise install && mise run setup   # pinned tooling, venv, locked dependencies
mise run products                # the whole document, product by product
mise run report                  # census, then strict report of every indexed product
mise run generate                # the modules, into ansible_collections/stephrobert/exoscale
mise run check                   # what a pull request must pass
mise run sanity                  # ansible-test sanity, refusing a green on zero files
mise run package                 # the installable archive, checked against plugins/ on disk
mise run security                # actionlint, zizmor, poutine on the workflows
mise run sync:api && mise run drift   # re-download the contract, then say what moved
```

## Layout

```text
generator/          the producer: source, parser, ir, classifier, overrides, ansible, renderer, report
scripts/            the launchers: sanity, package, release, drift, readme counters, falsification
specs/exoscale/     the versioned contract, and products.txt which indexes tags
ansible_collections/stephrobert/exoscale/   the deliverable, where Ansible expects it
tests/fixtures/gadget/   a laboratory contract reproducing the shapes of Exoscale
docs/               the generator, the contract, and what Scorecard says
.github/            the pipeline: every action pinned by SHA, no default permission
```

## Continuous integration

Every workflow starts with `permissions: {}`, pins every action by commit SHA
and checks out with `persist-credentials: false`. What runs:

| workflow | what it holds |
|---|---|
| `ci` | lint, types, tests, strict report, generated-artifact drift, changelog fragments, falsification, README counters; `ansible-test sanity` and `antsibull-docs` on ansible-core 2.17 to 2.21; the archive built, installed and queried |
| `Sécurité des workflows` | actionlint, zizmor, poutine, and the applied ruleset compared to `.github/rulesets/main.json` |
| `Plumber` | trust policy on third-party actions, from `.plumber.yaml` |
| `CodeQL`, `OSV-Scanner`, `Revue des dépendances`, `Secrets`, `SBOM`, `Scorecard` | static analysis, known vulnerabilities, licences, secrets, software bill of materials, posture |
| `dérive` | weekly: re-download the contract, count every product, open an issue when something moved |
| `release` | on a version tag only: the release guard, the whole `check`, sanity, the archive, then Galaxy |

## Licence

GPL-3.0-or-later. See `LICENSE`.
