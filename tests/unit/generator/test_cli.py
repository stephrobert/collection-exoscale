"""Le témoin du mode strict : il sort en 2 sur une opération non classée.

`report --strict` sort en 0 sur un dépôt sain comme sur un mode strict cassé :
un contrôle qui cherche une absence est indiscernable d'un contrôle qui n'a
rien regardé. Ce fichier plante le témoin, en fabriquant un contrat que
personne ne sait classer, et exige le code 2. Le code est ce dont la CI
dépend, donc c'est le code qui est mesuré, pas un message.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from generator.cli import EXIT_OK, EXIT_UNDECIDED, main

REPO_ROOT = Path(__file__).resolve().parents[3]
GADGET_INPUT = REPO_ROOT / "tests" / "fixtures" / "gadget" / "input"


def _spec_root(tmp_path: Path, *, with_unknown: bool) -> Path:
    """Le contrat de laboratoire, avec ou sans une opération que rien ne tranche.

    `PATCH` avec le verbe `frob` : aucune règle ne connaît ni l'un ni l'autre,
    et c'est le point. Le reste du contrat est celui du laboratoire, dont les
    autres tests prouvent déjà qu'il se classe entièrement.
    """
    racine = tmp_path / "specs"
    shutil.copytree(GADGET_INPUT, racine)
    if with_unknown:
        chemin = racine / "exoscale.v2.json"
        document = json.loads(chemin.read_text(encoding="utf-8"))
        document["paths"]["/gadget/{id}:frob"] = {
            "patch": {
                "operationId": "frob-gadget",
                "summary": "Frob a gadget",
                "tags": ["gadget"],
                "parameters": [
                    {"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}
                ],
                "responses": {
                    "200": {
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/operation"}
                            }
                        }
                    }
                },
            }
        }
        chemin.write_text(json.dumps(document), encoding="utf-8")
    return racine


def _report(tmp_path: Path, racine: Path, *, strict: bool) -> int:
    arguments = [
        "--spec-root",
        str(racine),
        "report",
        "gadget",
        "--output-dir",
        str(tmp_path / "reports"),
    ]
    if strict:
        arguments.append("--strict")
    return main(arguments)


def test_le_mode_strict_sort_en_2_sur_une_operation_non_classee(tmp_path: Path) -> None:
    """Le témoin. Sans lui, un mode strict cassé se lirait comme un dépôt sain."""
    racine = _spec_root(tmp_path, with_unknown=True)
    assert _report(tmp_path, racine, strict=True) == EXIT_UNDECIDED


def test_sans_strict_le_rapport_dit_et_ne_refuse_pas(tmp_path: Path) -> None:
    """Le contre-exemple : c'est `--strict` qui transforme le constat en refus."""
    racine = _spec_root(tmp_path, with_unknown=True)
    assert _report(tmp_path, racine, strict=False) == EXIT_OK


def test_le_mode_strict_sort_en_0_quand_tout_est_classe(tmp_path: Path) -> None:
    """Le cas voisin : un mode strict qui refuse tout ferait passer le témoin."""
    racine = _spec_root(tmp_path, with_unknown=False)
    assert _report(tmp_path, racine, strict=True) == EXIT_OK
