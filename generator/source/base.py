"""Accès au contrat versionné qui décrit l'API v2 d'Exoscale.

**Un seul document pour tous les produits.** C'est l'écart structurel le plus
important avec Scaleway, où un fichier vaut un produit. Exoscale publie un
document OpenAPI 3.0 unique (`https://openapi-v2.exoscale.com/source.json`,
mesuré : 261 chemins, 374 opérations, 55 tags dont 12 parents) et c'est le
**tag** qui dit à quel produit une opération appartient : `instance` a pour
parent `compute`, `vpc-subnet` a pour parent `vpc` qui a pour parent
`compute`.

`specs/exoscale/products.txt` indexe donc des tags racines, pas des fichiers,
et cette couche **découpe** le document par famille de tags avant de le
confier au parser. Le parser ne sait rien des tags : il reçoit un document
dont `paths` ne porte que les opérations du produit demandé, et il traduit.

Le générateur ne lit jamais le réseau pendant une génération : le
téléchargement est une opération séparée (`mise run sync:api`), et une
évolution de l'API arrive comme un diff dans une revue.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

#: Racine des documents versionnés, relative à la racine du dépôt.
DEFAULT_SPEC_ROOT = Path(__file__).resolve().parents[2] / "specs" / "exoscale"

#: Nom du fichier de contrat, par version : `exoscale.v2.json`.
DOCUMENT_STEM = "exoscale"

#: Méthodes HTTP qu'un chemin OpenAPI peut porter.
_METHODS: tuple[str, ...] = ("get", "post", "put", "patch", "delete")


class SpecNotFoundError(FileNotFoundError):
    """Le document demandé n'est pas présent dans la copie versionnée."""


class ProductNotFoundError(LookupError):
    """Le produit demandé n'est pas dans `products.txt`, ou aucun tag ne le porte."""


@dataclass(frozen=True)
class ProductEntry:
    """Une ligne de `products.txt` : `<tag-racine> [<nom-produit>] <version>`."""

    tag: str
    product: str
    version: str


@dataclass(frozen=True)
class SpecDocument:
    """Le contrat d'un produit, découpé et prêt pour le parser."""

    product: str
    version: str
    path: Path
    #: Le document OpenAPI, dont `paths` ne porte que les opérations du produit.
    document: dict[str, Any]
    #: Les tags de la famille du produit, tag racine compris.
    tags: tuple[str, ...] = ()

    @property
    def slug(self) -> str:
        return f"{self.product}.{self.version}"


@dataclass(frozen=True)
class ProductCensus:
    """Ce que le document contient, produit par produit, avant tout découpage.

    C'est la mesure qui garde visible ce que `products.txt` n'indexe pas : une
    opération hors périmètre n'est pas perdue, elle est comptée ici.
    """

    #: Nombre d'opérations par tag racine.
    by_root: dict[str, int] = field(default_factory=dict)
    #: Tags portés par des opérations mais absents de la liste `tags` du document.
    undeclared_tags: tuple[str, ...] = ()
    #: Opérations sans aucun tag, donc rattachables à aucun produit.
    untagged: tuple[str, ...] = ()
    #: Opérations dont les tags désignent plusieurs racines.
    multi_root: tuple[str, ...] = ()
    #: Nombre d'opérations distinctes du document, tags ou pas.
    operations: int = 0

    @property
    def total(self) -> int:
        """Le nombre d'opérations distinctes : une opération à cheval sur deux
        produits compte une fois ici, et une fois dans chaque produit."""
        return self.operations


def read_products(root: Path = DEFAULT_SPEC_ROOT) -> list[ProductEntry]:
    """Lit l'index : `<tag-racine> [<nom-produit>] <version>`, commentaires ignorés."""
    index = root / "products.txt"
    if not index.is_file():
        raise SpecNotFoundError(f"index absent : {index}")
    entries: list[ProductEntry] = []
    for line in index.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        if len(fields) == 2:
            tag, version = fields
            product = tag
        elif len(fields) == 3:
            tag, product, version = fields
        else:
            raise ValueError(f"{index} : ligne mal formée : {line!r}")
        entries.append(ProductEntry(tag=tag, product=product, version=version))
    return entries


def tag_roots(document: dict[str, Any]) -> dict[str, str]:
    """Pour chaque tag déclaré, son tag racine (le tag sans parent).

    Un tag qui se déclare lui-même parent, directement ou par un cycle, est
    rattaché à lui-même plutôt que de faire boucler la résolution.
    """
    parent_of: dict[str, str | None] = {
        str(tag["name"]): tag.get("parent") for tag in document.get("tags", [])
    }
    roots: dict[str, str] = {}
    for name in parent_of:
        current = name
        seen: set[str] = set()
        while parent_of.get(current) and current not in seen:
            seen.add(current)
            current = str(parent_of[current])
        roots[name] = current
    return roots


def root_of(tag: str, roots: dict[str, str]) -> str:
    """La racine d'un tag ; un tag non déclaré est sa propre racine.

    Mesuré sur le contrat : `ccm`, `organization` et `quotas` sont portés par
    des opérations sans figurer dans la liste des tags. Les rattacher à
    eux-mêmes les garde visibles dans le recensement plutôt que de les perdre.
    """
    return roots.get(tag, tag)


def census(document: dict[str, Any]) -> ProductCensus:
    """Recense les opérations du document par produit, sans rien filtrer."""
    roots = tag_roots(document)
    by_root: Counter[str] = Counter()
    undeclared: set[str] = set()
    untagged: list[str] = []
    multi_root: list[str] = []
    operations = 0
    for path, item in document.get("paths", {}).items():
        for method in _METHODS:
            operation = item.get(method)
            if operation is None:
                continue
            operations += 1
            identifier = str(operation.get("operationId") or f"{method.upper()} {path}")
            tags = [str(tag) for tag in operation.get("tags") or ()]
            if not tags:
                untagged.append(identifier)
                continue
            undeclared.update(tag for tag in tags if tag not in roots)
            found = {root_of(tag, roots) for tag in tags}
            if len(found) > 1:
                multi_root.append(identifier)
            for root in sorted(found):
                by_root[root] += 1
    return ProductCensus(
        by_root=dict(sorted(by_root.items())),
        undeclared_tags=tuple(sorted(undeclared)),
        untagged=tuple(sorted(untagged)),
        multi_root=tuple(sorted(multi_root)),
        operations=operations,
    )


def split_product(document: dict[str, Any], tag: str) -> tuple[dict[str, Any], tuple[str, ...]]:
    """Découpe le document : ne garde que les opérations de la famille de `tag`.

    Une opération appartient au produit si l'un de ses tags a `tag` pour
    racine. Une opération à plusieurs tags de la même famille n'est gardée
    qu'une fois, puisqu'elle n'existe qu'une fois.
    """
    roots = tag_roots(document)
    family = tuple(sorted(name for name, root in roots.items() if root == tag))
    if tag not in roots and tag not in family:
        # Un tag non déclaré peut quand même être porté par des opérations.
        family = (tag,)

    paths: dict[str, Any] = {}
    for path, item in document.get("paths", {}).items():
        kept: dict[str, Any] = {key: value for key, value in item.items() if key not in _METHODS}
        found = False
        for method in _METHODS:
            operation = item.get(method)
            if operation is None:
                continue
            tags = [str(name) for name in operation.get("tags") or ()]
            if any(root_of(name, roots) == tag for name in tags):
                kept[method] = operation
                found = True
        if found:
            paths[path] = kept

    if not paths:
        raise ProductNotFoundError(
            f"aucune opération ne porte un tag de la famille {tag!r} ; "
            f"vérifier le tag sur https://openapi-v2.exoscale.com/"
        )
    cut = dict(document)
    cut["paths"] = paths
    return cut, family


@dataclass(frozen=True)
class VendoredSpecSource:
    """Lit `specs/exoscale/exoscale.<version>.json` et le découpe par produit."""

    root: Path = DEFAULT_SPEC_ROOT

    def document_path(self, version: str) -> Path:
        return self.root / f"{DOCUMENT_STEM}.{version}.json"

    def load_document(self, version: str) -> dict[str, Any]:
        """Le document entier, tel que publié, sans découpage."""
        path = self.document_path(version)
        if not path.is_file():
            raise SpecNotFoundError(
                f"contrat absent : {path}. Lancer `mise run sync:api` pour le télécharger."
            )
        with path.open(encoding="utf-8") as handle:
            document = json.load(handle)
        if not isinstance(document, dict) or "paths" not in document:
            raise ValueError(f"{path} ne contient pas un document OpenAPI")
        return document

    def load(self, product: str, version: str) -> SpecDocument:
        """Le contrat du produit, découpé selon `products.txt`."""
        entry = next(
            (
                item
                for item in read_products(self.root)
                if item.version == version and product in (item.product, item.tag)
            ),
            None,
        )
        if entry is None:
            raise ProductNotFoundError(
                f"produit {product!r} ({version}) absent de {self.root / 'products.txt'}"
            )
        document = self.load_document(version)
        cut, family = split_product(document, entry.tag)
        return SpecDocument(
            product=entry.product,
            version=version,
            path=self.document_path(version),
            document=cut,
            tags=family,
        )

    def available(self) -> list[tuple[str, str]]:
        """Les couples (produit, version) que l'index déclare, dans son ordre."""
        return [(entry.product, entry.version) for entry in read_products(self.root)]
