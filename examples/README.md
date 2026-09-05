# The example platform, and what it proves

This directory carries a **complete platform** deployed by Terraform, and the
playbook that operates it with the collection. It does not exist to look nice:
it is the bench on which what the collection can do gets proven.

```text
examples/stack/               the Terraform stack: one platform, two targets
examples/playbooks/           the dynamic inventory and the modules playbook
examples/callback_plugins/    journal.py, what really ran
```

## Terraform, and the floor it stands on

The first version of this platform was built through the Python SDK, because
the Exoscale Terraform provider honoured `EXOSCALE_API_ENDPOINT` for only one
of its two clients: an `apply` **split** between the emulator and a paying
account, in a single run. Upstream fixed it in provider 0.71.0, and feint
lifted its refusal on a measurement rather than on the release note, with the
control that gives the measurement its meaning:

| provider | apply | second plan | destroy | hosts on the wire |
|---|---|---|---|---|
| v0.70.0 | 15 created | no changes | 15 destroyed | 57 requests to `api-ch-*.exoscale.com` |
| v0.71.0 | 15 created | no changes | 15 destroyed | none |

Two ways of building the same platform always end up diverging, so the SDK
platform is gone: the stack is the only source. Three barriers keep it safe,
and none rests on the other two: `providers.tf` pins **exactly** 0.71.0, the
emulator refuses an older provider by its user agent, and the launcher reads
the version `terraform init` resolved and refuses to apply below the floor.

The provider has no endpoint attribute. It reads `EXOSCALE_API_ENDPOINT` from
the environment, `/v2` included, which `feint env exoscale` prints and the
launcher passes on. The stack's `endpoint` variable only switches the
credentials to the emulator's fake pair: a stack pointed at the emulator
without that environment fails with a 403 from the real API instead of
creating anything there.

## What the platform contains

Twenty-three resources:

* a **bastion**, the only machine holding an elastic IP;
* two **web** machines and two **application** machines with no public
  address, on a managed private network `backend`, the application ones also
  on `monitoring` and in an anti-affinity group;
* an **instance pool** of one machine and a **load balancer** serving it;
* a **Block Storage volume** attached to one application machine, and its
  snapshot;
* one security group per tier, with its rules, and the SSH key of the
  exercise.

Everything the API can label carries `exemple=<run_id>`; the rest carries the
`exo-<run_id>` prefix in its name. The state lives beside the stack and is
never committed; the lock file is, because it carries the provider's hashes.

**What it does not contain, and why.** Provider 0.71.0 has no resource for an
instance snapshot, and the collection creates none (`create-snapshot` is
LIFECYCLE, Terraform's realm), so the snapshot the SDK platform used to take
is gone with it. The playbook asserts its absence rather than staying silent,
and `compute_snapshot_action` is declared without a target, with that
measurement as the reason.

## Why this shape

A fleet where every machine has a public address would prove nothing of the
inventory plugin. Here **four machines out of five have none**: reaching them
means reading the leases of each private network and choosing the right
address on the right network, which is exactly what the plugin does. It is
checked on every run.

## Two targets, one stack

```bash
mise run example            # feint, control plane only, offline, free
mise run example:reel       # the real Exoscale organization, billed
```

**The real target never runs without the maintainer's explicit agreement,
asked each time.** It spends money on their account, and a resource surviving
a failed run is a paid residue. The launcher refuses it without the
`--compte-reel-accorde` flag, and the emulator target is where the work
happens: everything above was written and exercised against feint.

## What a run leaves behind

Nothing on the cloud, and one artefact under `build/example/`: which modules
actually ran, derived from a callback plugin that listens to Ansible rather
than from the playbook text, and the tooling that produced it, feint,
Terraform and the provider by version. A task skipped by a `when`, and a route
feint declines with a 404 `feint does not serve`, do not count as covered.

```bash
mise run coverage:example   # the tiers of coverage, and what the last run played
mise run coverage:check     # the gate: every shipped module is called, or declared with its reason
```

Measured on 5 September 2026, against feint built from `main` at 9074c0f
(the published 0.12.1 still refuses the provider): 23 resources applied and
destroyed, no residue, 29 modules played, 2 idempotences proven, 9 routes
declined by feint and named. feint serves 104 of the 374 operations of the
contract, all of compute except the VPC beta, the console and the password,
all of block-storage, quotas, the audit trail and the organization read.
DBaaS, SKS, AI, IAM, KMS, DNS and SOS are not served, and their modules are
declared without a target, with that measurement as the reason.
