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
exoscale v2: 374 operations in a single document, 14 products counted, 1 indexed
  compute v2: 111 operations, 70 asynchronous
    INFO 35 · ACTION 18 · MANAGE 11 · WORKFLOW 0 · LIFECYCLE 34 · IGNORE 13 · UNKNOWN 0
    Day-2 64 · AUTO 64 · OVERRIDE 0 · classified for automatic generation 100.0% (64/64)

collection stephrobert.exoscale: 26 modules written, 39 planned, 13 set aside with their reason
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
  266 unit tests · 23 guards proven by mise run falsify
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
