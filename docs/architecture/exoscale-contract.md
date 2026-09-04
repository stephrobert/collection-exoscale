# The Exoscale contract: its source, its limits, its surveillance

The generator reads an **OpenAPI 3.0** document published by Exoscale and
versioned in `specs/exoscale/exoscale.v2.json`. This page says where it comes
from, what it carries, what it does not, and how the repository notices that
it moved. Every measurement dates from 4 September 2026.

## The source

A single document for every product, served at two addresses:

| address | paths | note |
|---|---|---|
| `https://openapi-v2.exoscale.com/source.json` | 261 | source of the reference documentation, and the copy embedded in the Python SDK |
| `https://community.exoscale.com/reference/api/exoscale-openapi-spec.json` | 259 | without `/ai/api-key/{id}/reveal` nor `/ai/api-key/{id}/rotate` |

`mise run sync:api` downloads the first one, byte for byte. `openapi: 3.0.0`,
`info.version: 2.0.0`, server `https://api-{zone}.exoscale.com/v2` with eight
enumerated zones.

## What the document carries

374 operations, 303 schemas, 55 tags of which 12 are parents. For each
operation: an `operationId` in kebab-case (`start-instance`), tags that say
the product, path parameters typed for the most part, a request body with
`required` on 64 bodies out of 142, and a success response.

Three response shapes: 81 GET answer with a reference (the resource), 50 with
an inline object holding one property (a list or object envelope), 2 with a
bare array. **203 writes answer with the `operation` schema**: the API accepts
the work and returns its identifier, and the result is read by polling
`get-operation` until `success`, `failure` or `timeout`.

## What the document does not carry

* **no pagination.** No `page`, `limit`, `offset` or `cursor` parameter. The
  parser reports it once per product;
* **44 path parameters without a schema** (`{name}`, `{service-name}`,
  `{username}`). The type is unknown and is settled by a `type` override;
* **3 tags used without being declared** (`ccm`, `organization`, `quotas`)
  and **2 operations without any tag** (`get-impact-estimate`,
  `get-impact-report`). The census names them;
* **no authentication declaration** (`securitySchemes` is empty). The
  `EXO2-HMAC-SHA256` scheme is documented apart
  (`https://openapi-v2.exoscale.com/topic/topic-api-request-signature`) and
  computed by the SDK;
* **no expected state after an action.** `operation.state == success` says
  the work is done, not that the instance is `running`.

## Two roles that never merge

| role | who holds it |
|---|---|
| describing the API for generation | the document versioned in `specs/exoscale/` |
| calling the API at runtime | the official Python SDK `exoscale`, generated from the same document |

The SDK embeds its own copy of the contract and derives its methods from it
(`operationId.replace("-", "_")`). A test requires the installed SDK to expose
every method a generated module calls: when the two copies diverge, that is
where it shows.

## How the repository notices a drift

Three mechanisms, and a weekly workflow that feeds them:

1. the contract is **versioned**: an upstream change arrives as a diff;
2. the **IR golden** (`tests/fixtures/<product>/expected_ir.json`) fails the
   CI as soon as an operation, a parameter or an enum moves in an indexed
   product;
3. the **strict report** exits 2 on any unclassified operation and any orphan
   override.

One document for fourteen products changes what the drift report must say:
the golden only covers indexed products, so `scripts/drift_report.py`
compares the **census** of the versioned document to the census of the
downloaded one, product by product, indexed or not, before looking at the
golden. It is the only measurement that sees what is not followed yet.

## Reproducing the measurements

```bash
curl -sL -o /dev/null -w '%{http_code} %{size_download}\n' https://openapi-v2.exoscale.com/source.json
mise run sync:api
python -m generator products --classify
python -m generator inspect compute
python -m generator report compute --strict
```
