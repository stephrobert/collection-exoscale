"""Interface en ligne de commande du générateur.

    python -m generator products                 # ce que le document contient, produit par produit
    python -m generator inspect compute          # ce que le contrat du produit contient
    python -m generator classify compute         # la décision, opération par opération
    python -m generator report compute --strict  # les rapports, texte, JSON et Markdown
    python -m generator generate compute         # les modules, dans plugins/modules

Codes de sortie, la CI en dépend :

* ``0`` succès ;
* ``1`` erreur d'exécution (contrat absent, override invalide, modèle
  impossible à construire) ;
* ``2`` le rapport contient une opération non classée ou un override orphelin,
  avec ``--strict``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from generator.ansible.collection import CollectionError, load_collection
from generator.ansible.models import ModuleModelError, build_module_specs
from generator.classifier.rules import classify
from generator.ir.enums import OperationKind
from generator.overrides.loader import OverrideError
from generator.parser.openapi import ParseError, parse_document
from generator.plan import ProductPlan, build_plan
from generator.renderer.modules import write_modules
from generator.report import render
from generator.source.base import (
    DEFAULT_SPEC_ROOT,
    ProductNotFoundError,
    SpecDocument,
    SpecNotFoundError,
    VendoredSpecSource,
    census,
    split_product,
)

ROOT = Path(__file__).resolve().parents[1]

#: Version de l'API par défaut. Exoscale n'en publie qu'une : la v2.
DEFAULT_VERSION = "v2"

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_UNDECIDED = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m generator",
        description="Générateur de modules Ansible Day-2 pour l'API v2 d'Exoscale.",
    )
    parser.add_argument(
        "--spec-root",
        type=Path,
        default=DEFAULT_SPEC_ROOT,
        help="racine des contrats versionnés (défaut : specs/exoscale)",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    products = subcommands.add_parser(
        "products", help="recenser le document entier, produit par produit"
    )
    products.add_argument("--api-version", dest="api_version", default=DEFAULT_VERSION)
    products.add_argument(
        "--classify",
        action="store_true",
        help="classer chaque produit avec les seules règles, sans override, et compter",
    )

    for name, help_text in (
        ("inspect", "afficher ce que le contrat du produit déclare"),
        ("classify", "afficher la classification, opération par opération"),
        ("report", "produire les rapports de couverture"),
        ("generate", "écrire les modules Ansible dans plugins/modules"),
    ):
        subcommand = subcommands.add_parser(name, help=help_text)
        subcommand.add_argument("product", help="produit Exoscale, par exemple compute")
        subcommand.add_argument(
            "--api-version", dest="api_version", default=DEFAULT_VERSION, help="défaut : v2"
        )

    report = subcommands.choices["report"]
    report.add_argument(
        "--output-dir",
        type=Path,
        default=Path("build/reports"),
        help="répertoire des rapports JSON et Markdown",
    )
    report.add_argument(
        "--strict",
        action="store_true",
        help="sortir en 2 si une opération n'est pas classée ou si un override est orphelin",
    )

    generate = subcommands.choices["generate"]
    generate.add_argument(
        "--report-dir",
        type=Path,
        default=Path("build/reports"),
        help="répertoire où verser le compte rendu de génération",
    )
    generate.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="répertoire des modules produits (défaut : celui de la collection)",
    )
    generate.add_argument(
        "--module",
        action="append",
        dest="modules",
        default=[],
        metavar="NOM",
        help="restreindre la production aux modules nommés ; répétable",
    )
    generate.add_argument(
        "--collection-root",
        type=Path,
        default=None,
        help="racine de la collection (défaut : découverte sous ansible_collections/)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    version: str = arguments.api_version

    try:
        if arguments.command == "products":
            return _products(version, arguments.spec_root, classify_all=arguments.classify)
        if arguments.command == "inspect":
            return _inspect(arguments.product, version, arguments.spec_root)
        plan = build_plan(arguments.product, version, spec_root=arguments.spec_root)
    except (SpecNotFoundError, ProductNotFoundError) as error:
        print(f"erreur : {error}", file=sys.stderr)
        return EXIT_ERROR
    except (ParseError, OverrideError, ValueError) as error:
        print(f"erreur : {error}", file=sys.stderr)
        return EXIT_ERROR

    if arguments.command == "classify":
        print(render.to_text(plan), end="")
        return EXIT_OK

    if arguments.command == "generate":
        try:
            return _generate(plan, arguments)
        except (CollectionError, ModuleModelError) as error:
            print(f"erreur : {error}", file=sys.stderr)
            return EXIT_ERROR

    output_dir: Path = arguments.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    slug = plan.service.slug
    (output_dir / f"{slug}.json").write_text(render.to_json(plan), encoding="utf-8")
    (output_dir / f"{slug}.md").write_text(render.to_markdown(plan), encoding="utf-8")
    print(render.to_text(plan), end="")
    print(f"\nrapports écrits dans {output_dir}/{slug}.{{json,md}}")

    if arguments.strict and (plan.unknown or plan.orphan_overrides):
        print(
            f"\n{len(plan.unknown)} opération(s) non classée(s), "
            f"{len(plan.orphan_overrides)} override(s) orphelin(s)",
            file=sys.stderr,
        )
        return EXIT_UNDECIDED
    return EXIT_OK


def _products(version: str, spec_root: Path, *, classify_all: bool) -> int:
    """Recense le document entier : ce que `products.txt` indexe, et le reste.

    C'est la mesure qui empêche une opération de disparaître dans le silence
    d'un produit non indexé : chaque tag racine est compté, les tags employés
    sans être déclarés sont nommés, et les opérations sans tag aussi.
    """
    source = VendoredSpecSource(root=spec_root)
    document = source.load_document(version)
    recensement = census(document)
    indexed = {product: tag for product, tag in _index(source)}

    print(f"exoscale {version} : {recensement.total} opérations, {len(document['paths'])} chemins")
    print()
    print(f"  {'produit (tag racine)':<24} {'opérations':>10}  indexé   unknown")
    for root, count in recensement.by_root.items():
        marque = "oui" if root in indexed.values() else "non"
        unknown = ""
        if classify_all:
            cut, _ = split_product(document, root)
            spec = SpecDocument(
                product=root, version=version, path=source.document_path(version), document=cut
            )
            service = parse_document(spec)
            inconnues = sum(
                1
                for operation in service.operations
                if classify(operation).kind is OperationKind.UNKNOWN
            )
            unknown = f"{inconnues:>7}"
        print(f"  {root:<24} {count:>10}  {marque:<6} {unknown}")

    if recensement.undeclared_tags:
        print()
        print(
            f"  {len(recensement.undeclared_tags)} tag(s) employé(s) sans être déclaré(s) : "
            + ", ".join(recensement.undeclared_tags)
        )
    if recensement.multi_root:
        print(
            f"  {len(recensement.multi_root)} opération(s) à cheval sur deux produits : "
            + ", ".join(recensement.multi_root)
        )
    if recensement.untagged:
        print(
            f"  {len(recensement.untagged)} opération(s) sans tag, rattachable(s) à aucun "
            "produit : " + ", ".join(recensement.untagged)
        )
    return EXIT_OK


def _index(source: VendoredSpecSource) -> list[tuple[str, str]]:
    from generator.source.base import read_products

    return [(entry.product, entry.tag) for entry in read_products(source.root)]


def _generate(plan: ProductPlan, arguments: argparse.Namespace) -> int:
    """Écrit les modules, et dit ce qu'il n'a pas écrit et pourquoi."""
    collection = load_collection(arguments.collection_root)
    output_dir = arguments.output_dir or collection.modules_dir
    specs, skipped = build_module_specs(plan, collection, only=tuple(arguments.modules))
    written = write_modules(
        specs,
        output_dir,
        source=f"specs/exoscale/{plan.service.source}",
    )

    affichage = output_dir.relative_to(ROOT) if output_dir.is_relative_to(ROOT) else output_dir
    print(f"{plan.service.slug} -> {affichage} (collection {collection.fqcn})")
    print()
    for spec in sorted(specs, key=lambda item: item.name):
        print(f"  écrit    {spec.name:<40} {', '.join(spec.operation_ids)}")

    if skipped:
        grouped: dict[str, list[str]] = {}
        for name, reason in skipped:
            grouped.setdefault(reason, []).append(name)
        print()
        for reason, names in sorted(grouped.items()):
            print(f"  écarté   {reason} ({len(names)})")
            print(f"           {', '.join(sorted(names))}")

    limits = sorted({limit for spec in specs for limit in spec.limits})
    if limits:
        print(f"\n{len(limits)} limite(s) du contrat rencontrée(s) au rendu :")
        for limit in limits:
            print(f"  {limit}")

    print(f"\n{len(written)} module(s) écrit(s).")

    arguments.report_dir.mkdir(parents=True, exist_ok=True)
    compte_rendu = arguments.report_dir / f"{plan.service.slug}.generation.md"
    compte_rendu.write_text(
        render.to_generation_markdown(
            plan,
            written=[spec.name for spec in specs],
            skipped=skipped,
            limits=limits,
        ),
        encoding="utf-8",
    )
    return EXIT_OK


def _inspect(product: str, version: str, spec_root: Path) -> int:
    """Affiche le contenu du contrat sans le classer."""
    spec = VendoredSpecSource(root=spec_root).load(product, version)
    service = parse_document(spec)
    print(f"{service.title or service.name} ({service.slug})")
    print(f"  contrat    : {service.source}")
    print(f"  tags       : {', '.join(spec.tags)}")
    print(f"  zones      : {', '.join(service.zones)}")
    print(f"  opérations : {len(service.operations)}")
    print(f"  enums      : {len(service.enums)}")
    print()
    for operation in service.operations:
        flag = "async" if operation.is_async else ""
        print(
            f"  {operation.http_method.value:<7} {operation.id:<46} "
            f"{operation.resource:<28} {len(operation.parameters):>2} param. {flag}".rstrip()
        )
    if service.warnings:
        print(f"\n{len(service.warnings)} limite(s) relevée(s) :")
        for warning in service.warnings:
            print(f"  {warning}")
    return EXIT_OK
