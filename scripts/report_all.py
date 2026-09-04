"""Le recensement du document entier, puis le rapport de chaque produit indexé.

`python -m generator report` prend un produit, et c'est juste : il décrit une
famille de tags. Mais le document en porte quatorze, et une tâche qui n'en
rapporte qu'un laisserait les autres dans le silence. Le recensement vient
d'abord : il dit ce que `products.txt` indexe, ce qu'il n'indexe pas, et ce
qu'aucun tag ne rattache à un produit.

**La liste des produits n'est pas recopiée ici.** Elle vient de
`specs/exoscale/products.txt`.

Le code de sortie est le plus sévère rencontré, pas celui du dernier produit.

    python scripts/report_all.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generator.cli import main as generator_main
from generator.source.base import VendoredSpecSource

ROOT = Path(__file__).resolve().parents[1]
SPEC_ROOT = ROOT / "specs" / "exoscale"


def main() -> int:
    produits = list(VendoredSpecSource(root=SPEC_ROOT).available())
    if not produits:
        print(
            f"aucun produit dans {SPEC_ROOT.relative_to(ROOT)}/products.txt : "
            "un rapport qui ne mesure rien passerait pour un rapport vert.",
            file=sys.stderr,
        )
        return 1

    pire = generator_main(["products"])
    print()
    for produit, version in produits:
        code = generator_main(["report", produit, "--api-version", version, "--strict"])
        pire = max(pire, code)
        print()
    return pire


if __name__ == "__main__":
    raise SystemExit(main())
