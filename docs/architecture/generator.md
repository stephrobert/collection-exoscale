# Generator architecture

This repository does not contain a hand-written Ansible collection: it
contains the generator that writes it, and the decisions that turn a technical
API into a coherent Ansible interface. The source of the contract and its
measured limits are in [exoscale-contract.md](exoscale-contract.md).

## The pipeline

```text
specs/exoscale/exoscale.v2.json         versioned contract (OpenAPI 3.0), one for every product
        |
        v  generator/source/base.py     split by tag family (products.txt)
   SpecDocument                          the document, reduced to the product's paths
        |
        v  generator/parser/openapi.py
   ApiService                            canonical IR, without Ansible nor SDK
        |
        v  generator/classifier/rules.py
   Classification                        INFO ACTION MANAGE WORKFLOW LIFECYCLE IGNORE UNKNOWN
        |
        v  generator/overrides/*.yml
   ProductPlan                           decision + target module + reason
        |
        +--> generator/report/render.py  text, JSON, Markdown
        |
        +--> generator/ansible/models.py intermediate model
                    |
                    v  generator/renderer + templates/
             plugins/modules/*.py
                    |
                    v  plugins/module_utils/exoscale.py
             execution: official SDK, waiting for the operation, errors
```

## The structuring decisions

### 1. A product is a family of tags, not a file

Exoscale publishes a single document. `products.txt` indexes one root tag per
line, and the source keeps the operations one of whose tags climbs to that
root. `python -m generator products` counts the whole document so that what
is not indexed stays counted.

### 2. The operation key is stable

`compute.v2.Instance.start-instance`: product, version, resource, contract
identifier. It is the key of the overrides and of the report.

### 3. The resource is derived from the path

First and last meaningful segment, once identifiers, the `:verb` suffix and
the trailing action segment are removed. A trailing segment is an action
segment when its **first word is the verb** of the `operationId`, not only
when it equals it: `/kms-key/{id}/schedule-deletion` and
`/sks-cluster/{id}/rotate-ccm-credentials` carry multi-word action segments,
and strict equality turned twelve of them into resources, hence into phantom
modules (`kms_key_schedule_deletion_action`). Measured while indexing the
other thirteen products. The case where two collections share a name
(`vpc_route`) is corrected by an override, and the report shows it.

The module name does not repeat the product when the path already carries
it: `/sks-cluster` under `sks` gives the resource `sks_cluster` and the
module `sks_cluster_info`, not `sks_sks_cluster_info`. The override key and
the report keep the resource as derived; only the file name changes.

### 4. The classification rules are Exoscale's

| verb | method | class |
|---|---|---|
| `get`, `list` | GET | INFO |
| `reveal` | GET | INFO, sensitive value |
| `get`, `list` | POST | INFO |
| `create` | POST | LIFECYCLE |
| `delete` | DELETE | LIFECYCLE |
| `reset` | DELETE | ACTION |
| `update` | PUT, PATCH, POST | MANAGE |
| other | PUT, POST | ACTION |
| other | other | UNKNOWN |

Scaleway's six rules left 58 UNKNOWN out of 374; these leave zero on each of
the 14 products. A test plants a witness: a contract carrying an operation no
rule can settle makes `report --strict` exit 2, so that a broken strict mode
does not read like a healthy repository.

### 5. An action is an operation

An action module groups the one-shot operations of a resource
(`compute_instance_action`: `start`, `stop`, `reboot`, `scale`,
`resize_disk`, `reset_field`, `reset_password`, `add_protection`,
`remove_protection`, `enable_tpm`, `revert_to_snapshot`). The selector is the
path identifier common to all of them; an enumerated path parameter
(`{field}`) is an option; what the contract requires for one action only
becomes a `required_if`.

### 6. Asynchrony is a fact of the IR

`ApiResponse.is_operation` carries the fact; the plan counts asynchronous
operations; the runtime waits for the operation when `wait` is true and
returns the object in every case, with its `state`. An action that answers
at once (`enable-kms-key`, `resize-block-storage-volume`: nineteen of them
across the products) returns its response under `result`, never under
`operation`, and the module's `RETURN` documents which key each kind of
action fills.

Two kinds of write are set aside by override rather than rendered, each with
its reason in the report: the operations that **compute a value without
changing anything** (`encrypt`, `decrypt`, `generate-data-key`,
`assume-iam-role`, the Karpenter manifests), for which an action module would
report `changed` on nothing; and the operations that **schedule or cancel a
deletion**, which are the resource's lifecycle. The SKS kubeconfig, which has
its own resource in the path, is reclassified as a sensitive read.

### 7. Coverage names its denominator

```text
Day-2 coverage = (AUTO + OVERRIDE) / (INFO + ACTION + MANAGE + WORKFLOW)
```

Measured on compute: 64 Day-2 candidates out of 111 operations, 100%
classified for automatic generation. The generation report publishes next to
it the share carried by a written module, which is lower as long as MANAGE
has no renderer.

## Two goldens, two different measurements

* `tests/fixtures/<product>/expected_ir.json` freezes what the parser reads
  from the real contract. It moves when Exoscale moves;
* `tests/fixtures/gadget/expected_modules/` freezes what the renderer writes,
  from the laboratory contract. It must not move the day Exoscale adds an
  instance.

## What holds the produced file

The generator is not judged by the generator. `mise run sanity` runs
`ansible-test sanity` in place, and refuses a green obtained on zero examined
file: under a tree git does not track, `ansible-test` skips every target and
exits 0. `mise run package` builds the archive, checks that it carries
everything `plugins/` holds on disk and nothing from the repository, installs
it in a throwaway directory and asks `ansible-doc` for a module's
documentation. `mise run lint:docs` lets `antsibull-docs` judge the
cross-references that sanity lets through.

The lower bound of ansible-core is measured, not assumed: 2.16 fails two
Python 2 boilerplate checks these modules cannot satisfy, 2.17 to 2.21 pass
the same 24 checks. `meta/runtime.yml` says `>=2.17.0`, and the CI matrix
exercises every version it promises.

## What the project does not do

No `create`, no `delete`, no attachment between resources, no multi-cloud
abstraction. The boundary is set once:

```text
Terraform provisions resources. Ansible operates existing ones.
```
