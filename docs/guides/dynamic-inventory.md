# The Exoscale dynamic inventory

`stephrobert.exoscale.compute` builds an Ansible inventory from an Exoscale
organization. It discovers instances zone by zone, then links them to their
private networks through the leases of each network.

Everything this document claims is measured by the unit tests in
[tests/unit/inventory/](https://github.com/stephrobert/collection-exoscale/blob/main/tests/unit/inventory/).
Nothing has been played against a real organization yet, and there is no
emulator of the Exoscale API to play it against: that is written here rather
than implied.

## The configuration file

Ansible recognises an inventory plugin by the **file name**. It must end in
`exoscale.yml` or `exo.yml`, otherwise it is silently ignored:

```bash
ansible-inventory -i production.exoscale.yml --graph
```

The minimum fits on one line, and the environment provides the credentials:

```yaml
plugin: stephrobert.exoscale.compute
```

## Credentials

```bash
export EXOSCALE_API_KEY=... EXOSCALE_API_SECRET=...
```

`EXOSCALE_API_URL` is honoured: the API host normally carries the zone
(`api-{zone}.exoscale.com`), so the plugin builds one client per zone; with an
explicit URL, every zone talks to that host, which is what a local emulator
expects.

## Products

One hosting product is discovered, `instance`, and `all` (the default) means
that one. The engine is layered so that a second product costs a provider
file and one line in the discovery table, and a test requires that no core
layer names a product in its code.

## Zones

Without `zones`, the eight zones the API contract declares are queried, and a
test compares that list to the contract. A zone that refuses the product is
reported as a warning, not an error.

```yaml
zones:
  - ch-gva-2
  - de-fra-1
```

## Machine names

`hostnames` gives the sources of `inventory_hostname`, in order:

```yaml
hostnames:
  - label:role     # reads the value of the "role" label
  - name
  - id
```

Two instances may share a name. The plugin never lets the second overwrite
the first: the zone is appended, then the instance ID, and the collision is
reported.

## Addresses

`ansible_host` is chosen by family, in the order of `address_priority`, or
restricted to one private network:

```yaml
address:
  private_network: backend
require_address: true
```

Private addresses are not on the instance in the Exoscale API: they are the
**leases** of each private network. The plugin lists the networks of each
zone once, reads each network once, and joins in memory. The cost is one
list plus one read per network, never one call per machine.

## Filters

```yaml
labels:
  env: production
  role: ""            # the key exists, whatever its value
labels_match: any     # or all
states:
  - running
exclude:
  labels:
    decommissioned: ""
  states:
    - stopped
```

`list-instances` declares a `labels` filter, but the contract types it as a
bare string with no format, and the Python SDK encodes a mapping in no
documented way; feint refuses the parameter with a 400 for the same reason.
Any encoding chosen here would be an invented format, so the plugin never
sends it and filters locally on the normalised model. The cost is transferring
what gets discarded, which beats a filter nobody knows the API's reading of.

## Groups

`group_by` builds the native `exo_*` groups:

| axis | group |
|---|---|
| `product` | `exo_product_instance` |
| `zone` | `exo_zone_ch_gva_2` |
| `state` | `exo_state_running` |
| `labels` | `exo_label_env_prod`, one per key and value |
| `private_network` | `exo_private_network_backend` |
| `manager` | `exo_manager_instance_pool`, `exo_manager_<id>` |
| `type` | `exo_type_standard_medium` |

`manager` is worth a word: an instance that belongs to an instance pool or to
an SKS nodepool is relaunched by its manager, and a playbook stopping it by
hand should know.

`compose`, `groups` and `keyed_groups` are the standard Ansible mechanisms,
and they are applied on the host variables below.

## Host variables

```text
exoscale_id, exoscale_product, exoscale_name, exoscale_zone, exoscale_state
exoscale_labels                      the labels as a mapping
exoscale_public_ipv4, exoscale_public_ipv6
exoscale_private_ipv4, exoscale_private_ipv6
exoscale_private_networks            id, name, ipv4, ipv6 for each network
exoscale_manager_type, exoscale_manager_id
exoscale_address_source              which family gave ansible_host, or why none did
exoscale_instance                    type, template, ssh_key, disk_size, created_at, mac_address
exoscale_raw                         the API object, only with include_raw: true
```

`exoscale_id` and `exoscale_zone` are what lets a playbook chain on the Day-2
modules of the collection without a lookup.

## Failures are said, never swallowed

A refused credential stops the inventory: continuing would produce an empty
inventory that presents itself as complete. A missing permission on the
private networks is a warning: the machines are still listed, without their
private addresses. A zone that does not serve the product is a warning. With
`strict: true` (the default), any other failure fails the inventory; with
`strict: false`, it is reported and the rest is kept.

The `-vvv` output of `ansible-inventory` lists what happened: API calls,
leases indexed, hosts per provider, and the reason each filtered machine was
set aside.
