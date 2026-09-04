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
### ai (7 modules)

Exoscale AI services provide GPU-powered infrastructure for running machine learning workloads and large language models.

| module | what it does |
|---|---|
| `ai_deployment_action` | Perform an action on an Exoscale ai deployment |
| `ai_deployment_info` | Gather information about Exoscale ai deployments |
| `ai_inference_engine_parameter_info` | Gather information about Exoscale ai inference engine parameters |
| `ai_instance_type_info` | Gather information about Exoscale ai instance types |
| `ai_log_info` | Gather information about Exoscale ai logs |
| `ai_model_info` | Gather information about Exoscale ai models |
| `ai_quota_info` | Gather information about Exoscale ai quotas |

### audit_trail (1 modules)

The Exoscale audit-trail provides a mechanism to query past events performing mutations on resources which happened on an organization.

| module | what it does |
|---|---|
| `audit_trail_event_info` | Gather information about Exoscale events |

### block_storage (3 modules)

Exoscale's Block Storage offers persistent externally
                   attached volumes for your Compute instances.

| module | what it does |
|---|---|
| `block_storage_action` | Perform an action on an Exoscale block storage |
| `block_storage_info` | Gather information about Exoscale block storages |
| `block_storage_snapshot_info` | Gather information about Exoscale block storage snapshots |

### ccm (1 modules)

ccm.

| module | what it does |
|---|---|
| `ccm_quota_info` | Gather information about Exoscale quotas |

### compute (28 modules)

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
| `compute_load_balancer_service_action` | Perform an action on an Exoscale load balancer service |
| `compute_load_balancer_service_info` | Gather information about Exoscale load balancer services |
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

### dbaas (66 modules)

Databases as a Service (DBaaS) provides scalable and fully-managed database solutions with high availability and performance backed by Exoscale's Compute and Storage services.

| module | what it does |
|---|---|
| `dbaas_ca_certificate_info` | Gather information about Exoscale dbaas ca certificates |
| `dbaas_clickhouse_acl_config_info` | Gather information about Exoscale dbaas clickhouse acl configs |
| `dbaas_clickhouse_info` | Gather information about Exoscale dbaas clickhouses |
| `dbaas_clickhouse_maintenance_action` | Perform an action on an Exoscale dbaas clickhouse maintenance |
| `dbaas_clickhouse_password_action` | Perform an action on an Exoscale dbaas clickhouse password |
| `dbaas_clickhouse_password_info` | Gather information about Exoscale dbaas clickhouse passwords |
| `dbaas_clickhouse_role_info` | Gather information about Exoscale dbaas clickhouse roles |
| `dbaas_clickhouse_user_info` | Gather information about Exoscale dbaas clickhouse users |
| `dbaas_external_endpoint_datadog_info` | Gather information about Exoscale dbaas external endpoint datadogs |
| `dbaas_external_endpoint_elasticsearch_info` | Gather information about Exoscale dbaas external endpoint elasticsearches |
| `dbaas_external_endpoint_info` | Gather information about Exoscale dbaas external endpoints |
| `dbaas_external_endpoint_opensearch_info` | Gather information about Exoscale dbaas external endpoint opensearches |
| `dbaas_external_endpoint_prometheus_info` | Gather information about Exoscale dbaas external endpoint prometheus |
| `dbaas_external_endpoint_rsyslog_info` | Gather information about Exoscale dbaas external endpoint rsyslogs |
| `dbaas_external_endpoint_type_info` | Gather information about Exoscale dbaas external endpoint types |
| `dbaas_external_integration_info` | Gather information about Exoscale dbaas external integrations |
| `dbaas_external_integration_settings_datadog_info` | Gather information about Exoscale dbaas external integration settings datadogs |
| `dbaas_grafana_info` | Gather information about Exoscale dbaas grafanas |
| `dbaas_grafana_maintenance_action` | Perform an action on an Exoscale dbaas grafana maintenance |
| `dbaas_grafana_password_action` | Perform an action on an Exoscale dbaas grafana password |
| `dbaas_grafana_password_info` | Gather information about Exoscale dbaas grafana passwords |
| `dbaas_integration_info` | Gather information about Exoscale dbaas integrations |
| `dbaas_integration_type_info` | Gather information about Exoscale dbaas integration types |
| `dbaas_kafka_acl_config_info` | Gather information about Exoscale dbaas kafka acl configs |
| `dbaas_kafka_info` | Gather information about Exoscale dbaas kafkas |
| `dbaas_kafka_maintenance_action` | Perform an action on an Exoscale dbaas kafka maintenance |
| `dbaas_kafka_password_action` | Perform an action on an Exoscale dbaas kafka password |
| `dbaas_migration_status_info` | Gather information about Exoscale dbaas migration status |
| `dbaas_mysql_info` | Gather information about Exoscale dbaas mysqls |
| `dbaas_mysql_maintenance_action` | Perform an action on an Exoscale dbaas mysql maintenance |
| `dbaas_mysql_migration_action` | Perform an action on an Exoscale dbaas mysql migration |
| `dbaas_mysql_password_action` | Perform an action on an Exoscale dbaas mysql password |
| `dbaas_mysql_password_info` | Gather information about Exoscale dbaas mysql passwords |
| `dbaas_mysql_write_action` | Perform an action on an Exoscale dbaas mysql write |
| `dbaas_opensearch_acl_config_info` | Gather information about Exoscale dbaas opensearch acl configs |
| `dbaas_opensearch_info` | Gather information about Exoscale dbaas opensearches |
| `dbaas_opensearch_maintenance_action` | Perform an action on an Exoscale dbaas opensearch maintenance |
| `dbaas_opensearch_password_action` | Perform an action on an Exoscale dbaas opensearch password |
| `dbaas_opensearch_password_info` | Gather information about Exoscale dbaas opensearch passwords |
| `dbaas_postgres_info` | Gather information about Exoscale dbaas postgres |
| `dbaas_postgres_maintenance_action` | Perform an action on an Exoscale dbaas postgres maintenance |
| `dbaas_postgres_migration_action` | Perform an action on an Exoscale dbaas postgres migration |
| `dbaas_postgres_password_action` | Perform an action on an Exoscale dbaas postgres password |
| `dbaas_postgres_password_info` | Gather information about Exoscale dbaas postgres passwords |
| `dbaas_service_info` | Gather information about Exoscale dbaas services |
| `dbaas_service_log_info` | Gather information about Exoscale dbaas service logs |
| `dbaas_service_metric_info` | Gather information about Exoscale dbaas service metrics |
| `dbaas_service_type_info` | Gather information about Exoscale dbaas service types |
| `dbaas_settings_clickhouse_info` | Gather information about Exoscale dbaas settings clickhouses |
| `dbaas_settings_grafana_info` | Gather information about Exoscale dbaas settings grafanas |
| `dbaas_settings_kafka_info` | Gather information about Exoscale dbaas settings kafkas |
| `dbaas_settings_mysql_info` | Gather information about Exoscale dbaas settings mysqls |
| `dbaas_settings_opensearch_info` | Gather information about Exoscale dbaas settings opensearches |
| `dbaas_settings_pg_info` | Gather information about Exoscale dbaas settings pgs |
| `dbaas_settings_thanos_info` | Gather information about Exoscale dbaas settings thanos |
| `dbaas_settings_valkey_info` | Gather information about Exoscale dbaas settings valkeys |
| `dbaas_task_info` | Gather information about Exoscale dbaas tasks |
| `dbaas_thanos_info` | Gather information about Exoscale dbaas thanos |
| `dbaas_thanos_maintenance_action` | Perform an action on an Exoscale dbaas thanos maintenance |
| `dbaas_thanos_password_info` | Gather information about Exoscale dbaas thanos passwords |
| `dbaas_valkey_info` | Gather information about Exoscale dbaas valkeys |
| `dbaas_valkey_maintenance_action` | Perform an action on an Exoscale dbaas valkey maintenance |
| `dbaas_valkey_migration_action` | Perform an action on an Exoscale dbaas valkey migration |
| `dbaas_valkey_password_action` | Perform an action on an Exoscale dbaas valkey password |
| `dbaas_valkey_password_info` | Gather information about Exoscale dbaas valkey passwords |
| `dbaas_valkey_user_info` | Gather information about Exoscale dbaas valkey users |

### dns (3 modules)

DNS zone hosting and records management.

| module | what it does |
|---|---|
| `dns_domain_info` | Gather information about Exoscale dns domains |
| `dns_domain_record_info` | Gather information about Exoscale dns domain records |
| `dns_domain_zone_info` | Gather information about Exoscale dns domain zones |

### general (2 modules)

general.

| module | what it does |
|---|---|
| `general_operation_info` | Gather information about Exoscale operations |
| `general_zone_info` | Gather information about Exoscale zones |

### iam (5 modules)

Identity and Access Management: roles, users, policies and credentials for accessing the Exoscale API.

| module | what it does |
|---|---|
| `iam_api_key_info` | Gather information about Exoscale api keys |
| `iam_organization_policy_action` | Perform an action on an Exoscale iam organization policy |
| `iam_organization_policy_info` | Gather information about Exoscale iam organization policies |
| `iam_role_info` | Gather information about Exoscale iam roles |
| `iam_user_info` | Gather information about Exoscale users |

### kms (3 modules)

Exoscale Key Management Service is a managed security service that lets you create, control and manage the lifecycle of cryptographic keys.

| module | what it does |
|---|---|
| `kms_key_action` | Perform an action on an Exoscale kms key |
| `kms_key_info` | Gather information about Exoscale kms keys |
| `kms_key_rotation_info` | Gather information about Exoscale kms key rotations |

### organization (4 modules)

organization.

| module | what it does |
|---|---|
| `organization_env_impact_info` | Gather information about Exoscale env impacts |
| `organization_info` | Gather information about Exoscale organizations |
| `organization_live_balance_info` | Gather information about Exoscale live balances |
| `organization_usage_report_info` | Gather information about Exoscale usage reports |

### quotas (1 modules)

quotas.

| module | what it does |
|---|---|
| `quotas_quota_info` | Gather information about Exoscale quotas |

### sks (10 modules)

SKS is Exoscale's scalable Kubernetes service which provides
                   managed Kubernetes control planes with integrated support for
                   Exoscale instance pools ands network load balancers.

| module | what it does |
|---|---|
| `sks_cluster_action` | Perform an action on an Exoscale sks cluster |
| `sks_cluster_cert_info` | Gather information about Exoscale sks cluster certs |
| `sks_cluster_deprecated_resource_info` | Gather information about Exoscale sks cluster deprecated resources |
| `sks_cluster_info` | Gather information about Exoscale sks clusters |
| `sks_cluster_inspection_info` | Gather information about Exoscale sks cluster inspections |
| `sks_cluster_kubeconfig_info` | Gather information about Exoscale sks cluster kubeconfigs |
| `sks_cluster_nodepool_action` | Perform an action on an Exoscale sks cluster nodepool |
| `sks_cluster_nodepool_info` | Gather information about Exoscale sks cluster nodepools |
| `sks_cluster_version_info` | Gather information about Exoscale sks cluster versions |
| `sks_template_info` | Gather information about Exoscale sks templates |

### sos (2 modules)

Exoscale Simple Object Storage (SOS) is an S3-compatible object storage service.

| module | what it does |
|---|---|
| `sos_bucket_usage_info` | Gather information about Exoscale sos bucket usages |
| `sos_presigned_url_info` | Gather information about Exoscale sos presigned urls |
<!-- counters:end -->

## State

The modules import, their `argument_spec` is accepted by Ansible, the
installed SDK exposes every method they call, and `ansible-test sanity`
passes. They have not been played against the real cloud yet.

## Where to report a defect

This collection is generated. A defect in a module is not fixed in the
module, which the next generation rewrites: it belongs to the contract, to a
classification rule or to an override, in the repository linked above.
