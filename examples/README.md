# The example platform, and what it proves

This directory carries a **complete platform** built through the Exoscale SDK,
and the playbook that operates it with the collection. It does not exist to
look nice: it is the bench on which what the collection can do gets proven.

```text
examples/stack/platform.py    the platform, built and destroyed by the SDK
examples/playbooks/           the dynamic inventory and the modules playbook
examples/callback_plugins/    journal.py, what really ran
```

## Why the SDK and not Terraform

`feint env exoscale` says it plainly: the Exoscale Terraform provider honours
`EXOSCALE_API_ENDPOINT` for its egoscale v3 client and not for its v2 one, so
an `apply` would split between the emulator and the real cloud, with real
credentials in the environment. feint refuses to be pointed at by that
provider. The Python SDK honours the URL end to end, so the same platform is
built identically against feint and against the real organization, and only
the endpoint changes.

## What the platform contains

* a **bastion**, the only machine holding an elastic IP;
* two **web** machines and two **application** machines with no public
  address, on a managed private network `backend`, the application ones also
  on `monitoring` and in an anti-affinity group;
* an **instance pool** of one machine and a **load balancer** serving it;
* a **snapshot** of one application machine, a **Block Storage volume**
  attached to the other, and its snapshot;
* one security group per tier, and the SSH key of the exercise.

Everything carries the label `exemple=<run_id>`. Destruction reads the API
back to find what to remove, so an interrupted build is destroyed as
completely as a finished one: the truth is in the API, not in a local state.

## Why this shape

A fleet where every machine has a public address would prove nothing of the
inventory plugin. Here **four machines out of five have none**: reaching them
means reading the leases of each private network and choosing the right
address on the right network, which is exactly what the plugin does. It is
checked on every run.

## Two targets, one platform

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
than from the playbook text. A task skipped by a `when`, and a route feint
declines with a 404 `feint does not serve`, do not count as covered.

```bash
mise run coverage:example   # the tiers of coverage, and what the last run played
mise run coverage:check     # the gate: every shipped module is called, or declared with its reason
```

Measured on feint 0.12.1 on 5 September 2026: feint serves 104 of the 374
operations of the contract, all of compute except the VPC beta, the console
and the password, all of block-storage, quotas, the audit trail and the
organization read. DBaaS, SKS, AI, IAM, KMS, DNS and SOS are not served, and
their modules are declared without a target, with that measurement as the
reason.
