"""Régénère les golden fixtures depuis les contrats versionnés.

Un golden se met à jour délibérément : la commande est séparée des tests pour
qu'un diff inattendu apparaisse dans une revue, jamais dans un `pytest -u`.

Deux golden, et ils ne mesurent pas la même chose :

* `tests/fixtures/<produit>/expected_ir.json` fige ce que le **parser** lit du
  contrat réel. Il bouge quand Exoscale bouge ;
* `tests/fixtures/gadget/expected_modules/` fige ce que le **renderer** écrit,
  à partir du contrat de laboratoire. Il ne doit pas bouger le jour où
  Exoscale ajoute une instance.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from generator.ansible.collection import Collection
from generator.ansible.models import build_module_specs
from generator.overrides.loader import load_overrides
from generator.parser.openapi import parse_document
from generator.plan import plan_service
from generator.renderer.modules import write_modules
from generator.source.base import VendoredSpecSource

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
GADGET_SPECS = FIXTURES / "gadget" / "input"
GADGET_OVERRIDES = FIXTURES / "gadget" / "overrides"
GADGET_MODULES = FIXTURES / "gadget" / "expected_modules"

#: Identité figée pour le golden de rendu. Elle ne lit pas `galaxy.yml` : le
#: golden mesure le renderer, pas le namespace du jour.
LAB_COLLECTION = Collection(
    namespace="lab",
    name="gadget",
    version="9.9.9",
    path=FIXTURES / "gadget" / "ansible_collections" / "lab" / "gadget",
    authors=("Contrat de laboratoire (@lab)",),
)


def update_ir() -> None:
    """Fige l'IR de chaque produit indexé."""
    source = VendoredSpecSource(root=ROOT / "specs" / "exoscale")
    for product, version in source.available():
        service = parse_document(source.load(product, version))
        target = FIXTURES / product / "expected_ir.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(service.to_json(), encoding="utf-8")
        print(f"{target.relative_to(ROOT)} : {len(service.operations)} opérations")


def update_rendered_modules() -> None:
    """Fige les modules rendus depuis le contrat de laboratoire."""
    service = parse_document(VendoredSpecSource(root=GADGET_SPECS).load("gadget", "v2"))
    plan = plan_service(service, load_overrides("gadget", root=GADGET_OVERRIDES))
    specs, _ = build_module_specs(plan, LAB_COLLECTION)

    if GADGET_MODULES.exists():
        # Un module retiré du plan doit disparaître du golden, sinon le diff
        # ne dirait rien le jour où le renderer cesse de le produire.
        shutil.rmtree(GADGET_MODULES)
    written = write_modules(
        specs, GADGET_MODULES, source="tests/fixtures/gadget/input/exoscale.v2.json"
    )
    for path in written:
        print(f"{path.relative_to(ROOT)}")


def main() -> int:
    update_ir()
    update_rendered_modules()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
