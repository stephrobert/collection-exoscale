==================================
stephrobert.exoscale Release Notes
==================================

.. contents:: Topics

v0.1.0
======

Release Summary
---------------

First release of the collection. Every module is produced by the generator from the versioned Exoscale API v2 contract: information modules read one resource or list them, action modules trigger a one-shot operation on an existing resource and wait for the asynchronous operation to succeed. Nothing creates, deletes or links resources; Terraform provisions, this collection operates.

Minor Changes
-------------

- An action module that leads to a known state (``start``, ``stop``) reads the resource before acting and answers ``changed: false`` when the state is already reached; after the asynchronous operation succeeds, it reads the resource again and fails if the expected state is not observed. An action that always acts (``reboot``) never reports ``changed: false``. Check mode reports what would change without calling the API.
- An action that answers at once rather than with an operation returns its response under ``result`` instead of ``operation``, and its documentation says which actions wait and which do not.
- An information module without a list operation reads its resource unconditionally and requires every path identifier (``organization_info``, ``compute_load_balancer_service_info``); an action module accepts resources with zero or two shared identifiers (``iam_organization_policy_action``, ``sks_cluster_nodepool_action``).
- Every product of the Exoscale API v2 document is now indexed, fourteen root tags instead of one: ai, audit-trail, block-storage, ccm, compute, dbaas, dns, general, iam, kms, organization, quotas, sks and sos. Every operation of every product is classified with zero UNKNOWN; what is set aside (a relation Terraform declares, a deletion, a value computed without changing anything) is set aside with its reason in the generator's overrides.
- Module names no longer repeat the product when the API path already carries it: ``sks_cluster_info`` rather than ``sks_sks_cluster_info``.
- New inventory plugin ``stephrobert.exoscale.compute``. It discovers instances zone by zone with one API client per zone, reads the leases of every private network to give each machine its private addresses, names hosts from a chosen source (``name``, ``id``, an address family or ``label:KEY``) without ever letting two machines overwrite each other, chooses ``ansible_host`` by address family or by a named private network, builds ``exo_*`` groups by product, zone, state, label, private network, manager and instance type, and says why a machine was set aside. A refused credential fails the inventory; a missing permission on private networks is a warning.
- The inventory plugin gains ``default_zone`` (environment ``EXOSCALE_ZONE``), the zone recorded on hosts when ``api_url`` is set and ``zones`` is empty. A forced endpoint with neither fails the inventory rather than discovering nothing. Label filters are applied by the plugin itself: the API refuses the ``labels`` query parameter.
- The modules and the inventory plugin read the API endpoint from ``EXOSCALE_API_URL``, then from ``EXOSCALE_API_ENDPOINT``, the variable the Exoscale SDK and the feint emulator already use. The value carries the ``/v2`` suffix, and it replaces the zone-based host: every zone is served by that one endpoint.

New Plugins
-----------

Inventory
~~~~~~~~~

- stephrobert.exoscale.compute - Exoscale compute dynamic inventory.

New Modules
-----------

- stephrobert.exoscale.ai_deployment_action - Perform an action on an Exoscale ai deployment.
- stephrobert.exoscale.ai_deployment_info - Gather information about Exoscale ai deployments.
- stephrobert.exoscale.ai_inference_engine_parameter_info - Gather information about Exoscale ai inference engine parameters.
- stephrobert.exoscale.ai_instance_type_info - Gather information about Exoscale ai instance types.
- stephrobert.exoscale.ai_log_info - Gather information about Exoscale ai logs.
- stephrobert.exoscale.ai_model_info - Gather information about Exoscale ai models.
- stephrobert.exoscale.ai_quota_info - Gather information about Exoscale ai quotas.
- stephrobert.exoscale.audit_trail_event_info - Gather information about Exoscale events.
- stephrobert.exoscale.block_storage_snapshot_info - Gather information about Exoscale block storage snapshots.
- stephrobert.exoscale.block_storage_volume_action - Perform an action on an Exoscale block storage volume.
- stephrobert.exoscale.block_storage_volume_info - Gather information about Exoscale block storage volumes.
- stephrobert.exoscale.ccm_quota_info - Gather information about Exoscale quotas.
- stephrobert.exoscale.compute_anti_affinity_group_info - Gather information about Exoscale anti affinity groups.
- stephrobert.exoscale.compute_deploy_target_info - Gather information about Exoscale deploy targets.
- stephrobert.exoscale.compute_elastic_ip_action - Perform an action on an Exoscale elastic ip.
- stephrobert.exoscale.compute_elastic_ip_info - Gather information about Exoscale elastic ips.
- stephrobert.exoscale.compute_instance_action - Perform an action on an Exoscale instance.
- stephrobert.exoscale.compute_instance_console_info - Gather information about Exoscale instance consoles.
- stephrobert.exoscale.compute_instance_info - Gather information about Exoscale instances.
- stephrobert.exoscale.compute_instance_password_info - Gather information about Exoscale instance passwords.
- stephrobert.exoscale.compute_instance_pool_action - Perform an action on an Exoscale instance pool.
- stephrobert.exoscale.compute_instance_pool_info - Gather information about Exoscale instance pools.
- stephrobert.exoscale.compute_instance_type_info - Gather information about Exoscale instance types.
- stephrobert.exoscale.compute_load_balancer_action - Perform an action on an Exoscale load balancer.
- stephrobert.exoscale.compute_load_balancer_info - Gather information about Exoscale load balancers.
- stephrobert.exoscale.compute_load_balancer_service_action - Perform an action on an Exoscale load balancer service.
- stephrobert.exoscale.compute_load_balancer_service_info - Gather information about Exoscale load balancer services.
- stephrobert.exoscale.compute_private_network_action - Perform an action on an Exoscale private network.
- stephrobert.exoscale.compute_private_network_info - Gather information about Exoscale private networks.
- stephrobert.exoscale.compute_reverse_dns_elastic_ip_info - Gather information about Exoscale reverse dns elastic ips.
- stephrobert.exoscale.compute_reverse_dns_instance_info - Gather information about Exoscale reverse dns instances.
- stephrobert.exoscale.compute_security_group_info - Gather information about Exoscale security groups.
- stephrobert.exoscale.compute_snapshot_action - Perform an action on an Exoscale snapshot.
- stephrobert.exoscale.compute_snapshot_info - Gather information about Exoscale snapshots.
- stephrobert.exoscale.compute_ssh_key_info - Gather information about Exoscale ssh keys.
- stephrobert.exoscale.compute_template_info - Gather information about Exoscale templates.
- stephrobert.exoscale.compute_vpc_info - Gather information about Exoscale vpcs.
- stephrobert.exoscale.compute_vpc_route_info - Gather information about Exoscale vpc routes.
- stephrobert.exoscale.compute_vpc_subnet_info - Gather information about Exoscale vpc subnets.
- stephrobert.exoscale.compute_vpc_subnet_route_info - Gather information about Exoscale vpc subnet routes.
- stephrobert.exoscale.dbaas_ca_certificate_info - Gather information about Exoscale dbaas ca certificates.
- stephrobert.exoscale.dbaas_clickhouse_acl_config_info - Gather information about Exoscale dbaas clickhouse acl configs.
- stephrobert.exoscale.dbaas_clickhouse_info - Gather information about Exoscale dbaas clickhouses.
- stephrobert.exoscale.dbaas_clickhouse_maintenance_action - Perform an action on an Exoscale dbaas clickhouse maintenance.
- stephrobert.exoscale.dbaas_clickhouse_password_action - Perform an action on an Exoscale dbaas clickhouse password.
- stephrobert.exoscale.dbaas_clickhouse_password_info - Gather information about Exoscale dbaas clickhouse passwords.
- stephrobert.exoscale.dbaas_clickhouse_role_info - Gather information about Exoscale dbaas clickhouse roles.
- stephrobert.exoscale.dbaas_clickhouse_user_info - Gather information about Exoscale dbaas clickhouse users.
- stephrobert.exoscale.dbaas_external_endpoint_datadog_info - Gather information about Exoscale dbaas external endpoint datadogs.
- stephrobert.exoscale.dbaas_external_endpoint_elasticsearch_info - Gather information about Exoscale dbaas external endpoint elasticsearches.
- stephrobert.exoscale.dbaas_external_endpoint_info - Gather information about Exoscale dbaas external endpoints.
- stephrobert.exoscale.dbaas_external_endpoint_opensearch_info - Gather information about Exoscale dbaas external endpoint opensearches.
- stephrobert.exoscale.dbaas_external_endpoint_prometheus_info - Gather information about Exoscale dbaas external endpoint prometheus.
- stephrobert.exoscale.dbaas_external_endpoint_rsyslog_info - Gather information about Exoscale dbaas external endpoint rsyslogs.
- stephrobert.exoscale.dbaas_external_endpoint_type_info - Gather information about Exoscale dbaas external endpoint types.
- stephrobert.exoscale.dbaas_external_integration_info - Gather information about Exoscale dbaas external integrations.
- stephrobert.exoscale.dbaas_external_integration_settings_datadog_info - Gather information about Exoscale dbaas external integration settings datadogs.
- stephrobert.exoscale.dbaas_grafana_info - Gather information about Exoscale dbaas grafanas.
- stephrobert.exoscale.dbaas_grafana_maintenance_action - Perform an action on an Exoscale dbaas grafana maintenance.
- stephrobert.exoscale.dbaas_grafana_password_action - Perform an action on an Exoscale dbaas grafana password.
- stephrobert.exoscale.dbaas_grafana_password_info - Gather information about Exoscale dbaas grafana passwords.
- stephrobert.exoscale.dbaas_integration_info - Gather information about Exoscale dbaas integrations.
- stephrobert.exoscale.dbaas_integration_type_info - Gather information about Exoscale dbaas integration types.
- stephrobert.exoscale.dbaas_kafka_acl_config_info - Gather information about Exoscale dbaas kafka acl configs.
- stephrobert.exoscale.dbaas_kafka_info - Gather information about Exoscale dbaas kafkas.
- stephrobert.exoscale.dbaas_kafka_maintenance_action - Perform an action on an Exoscale dbaas kafka maintenance.
- stephrobert.exoscale.dbaas_kafka_password_action - Perform an action on an Exoscale dbaas kafka password.
- stephrobert.exoscale.dbaas_migration_status_info - Gather information about Exoscale dbaas migration status.
- stephrobert.exoscale.dbaas_mysql_info - Gather information about Exoscale dbaas mysqls.
- stephrobert.exoscale.dbaas_mysql_maintenance_action - Perform an action on an Exoscale dbaas mysql maintenance.
- stephrobert.exoscale.dbaas_mysql_migration_action - Perform an action on an Exoscale dbaas mysql migration.
- stephrobert.exoscale.dbaas_mysql_password_action - Perform an action on an Exoscale dbaas mysql password.
- stephrobert.exoscale.dbaas_mysql_password_info - Gather information about Exoscale dbaas mysql passwords.
- stephrobert.exoscale.dbaas_mysql_write_action - Perform an action on an Exoscale dbaas mysql write.
- stephrobert.exoscale.dbaas_opensearch_acl_config_info - Gather information about Exoscale dbaas opensearch acl configs.
- stephrobert.exoscale.dbaas_opensearch_info - Gather information about Exoscale dbaas opensearches.
- stephrobert.exoscale.dbaas_opensearch_maintenance_action - Perform an action on an Exoscale dbaas opensearch maintenance.
- stephrobert.exoscale.dbaas_opensearch_password_action - Perform an action on an Exoscale dbaas opensearch password.
- stephrobert.exoscale.dbaas_opensearch_password_info - Gather information about Exoscale dbaas opensearch passwords.
- stephrobert.exoscale.dbaas_postgres_info - Gather information about Exoscale dbaas postgres.
- stephrobert.exoscale.dbaas_postgres_maintenance_action - Perform an action on an Exoscale dbaas postgres maintenance.
- stephrobert.exoscale.dbaas_postgres_migration_action - Perform an action on an Exoscale dbaas postgres migration.
- stephrobert.exoscale.dbaas_postgres_password_action - Perform an action on an Exoscale dbaas postgres password.
- stephrobert.exoscale.dbaas_postgres_password_info - Gather information about Exoscale dbaas postgres passwords.
- stephrobert.exoscale.dbaas_service_info - Gather information about Exoscale dbaas services.
- stephrobert.exoscale.dbaas_service_log_info - Gather information about Exoscale dbaas service logs.
- stephrobert.exoscale.dbaas_service_metric_info - Gather information about Exoscale dbaas service metrics.
- stephrobert.exoscale.dbaas_service_type_info - Gather information about Exoscale dbaas service types.
- stephrobert.exoscale.dbaas_settings_clickhouse_info - Gather information about Exoscale dbaas settings clickhouses.
- stephrobert.exoscale.dbaas_settings_grafana_info - Gather information about Exoscale dbaas settings grafanas.
- stephrobert.exoscale.dbaas_settings_kafka_info - Gather information about Exoscale dbaas settings kafkas.
- stephrobert.exoscale.dbaas_settings_mysql_info - Gather information about Exoscale dbaas settings mysqls.
- stephrobert.exoscale.dbaas_settings_opensearch_info - Gather information about Exoscale dbaas settings opensearches.
- stephrobert.exoscale.dbaas_settings_pg_info - Gather information about Exoscale dbaas settings pgs.
- stephrobert.exoscale.dbaas_settings_thanos_info - Gather information about Exoscale dbaas settings thanos.
- stephrobert.exoscale.dbaas_settings_valkey_info - Gather information about Exoscale dbaas settings valkeys.
- stephrobert.exoscale.dbaas_task_info - Gather information about Exoscale dbaas tasks.
- stephrobert.exoscale.dbaas_thanos_info - Gather information about Exoscale dbaas thanos.
- stephrobert.exoscale.dbaas_thanos_maintenance_action - Perform an action on an Exoscale dbaas thanos maintenance.
- stephrobert.exoscale.dbaas_thanos_password_info - Gather information about Exoscale dbaas thanos passwords.
- stephrobert.exoscale.dbaas_valkey_info - Gather information about Exoscale dbaas valkeys.
- stephrobert.exoscale.dbaas_valkey_maintenance_action - Perform an action on an Exoscale dbaas valkey maintenance.
- stephrobert.exoscale.dbaas_valkey_migration_action - Perform an action on an Exoscale dbaas valkey migration.
- stephrobert.exoscale.dbaas_valkey_password_action - Perform an action on an Exoscale dbaas valkey password.
- stephrobert.exoscale.dbaas_valkey_password_info - Gather information about Exoscale dbaas valkey passwords.
- stephrobert.exoscale.dbaas_valkey_user_info - Gather information about Exoscale dbaas valkey users.
- stephrobert.exoscale.dns_domain_info - Gather information about Exoscale dns domains.
- stephrobert.exoscale.dns_domain_record_info - Gather information about Exoscale dns domain records.
- stephrobert.exoscale.dns_domain_zone_info - Gather information about Exoscale dns domain zones.
- stephrobert.exoscale.general_operation_info - Gather information about Exoscale operations.
- stephrobert.exoscale.general_zone_info - Gather information about Exoscale zones.
- stephrobert.exoscale.iam_api_key_info - Gather information about Exoscale api keys.
- stephrobert.exoscale.iam_organization_policy_action - Perform an action on an Exoscale iam organization policy.
- stephrobert.exoscale.iam_organization_policy_info - Gather information about Exoscale iam organization policies.
- stephrobert.exoscale.iam_role_info - Gather information about Exoscale iam roles.
- stephrobert.exoscale.iam_user_info - Gather information about Exoscale users.
- stephrobert.exoscale.kms_key_action - Perform an action on an Exoscale kms key.
- stephrobert.exoscale.kms_key_info - Gather information about Exoscale kms keys.
- stephrobert.exoscale.kms_key_rotation_info - Gather information about Exoscale kms key rotations.
- stephrobert.exoscale.organization_env_impact_info - Gather information about Exoscale env impacts.
- stephrobert.exoscale.organization_info - Gather information about Exoscale organizations.
- stephrobert.exoscale.organization_live_balance_info - Gather information about Exoscale live balances.
- stephrobert.exoscale.organization_usage_report_info - Gather information about Exoscale usage reports.
- stephrobert.exoscale.quotas_quota_info - Gather information about Exoscale quotas.
- stephrobert.exoscale.sks_cluster_action - Perform an action on an Exoscale sks cluster.
- stephrobert.exoscale.sks_cluster_cert_info - Gather information about Exoscale sks cluster certs.
- stephrobert.exoscale.sks_cluster_deprecated_resource_info - Gather information about Exoscale sks cluster deprecated resources.
- stephrobert.exoscale.sks_cluster_info - Gather information about Exoscale sks clusters.
- stephrobert.exoscale.sks_cluster_inspection_info - Gather information about Exoscale sks cluster inspections.
- stephrobert.exoscale.sks_cluster_kubeconfig_info - Gather information about Exoscale sks cluster kubeconfigs.
- stephrobert.exoscale.sks_cluster_nodepool_action - Perform an action on an Exoscale sks cluster nodepool.
- stephrobert.exoscale.sks_cluster_nodepool_info - Gather information about Exoscale sks cluster nodepools.
- stephrobert.exoscale.sks_cluster_version_info - Gather information about Exoscale sks cluster versions.
- stephrobert.exoscale.sks_template_info - Gather information about Exoscale sks templates.
- stephrobert.exoscale.sos_bucket_usage_info - Gather information about Exoscale sos bucket usages.
- stephrobert.exoscale.sos_presigned_url_info - Gather information about Exoscale sos presigned urls.
