"""Un module généré se vérifie en l'important et en construisant son argument_spec.

Le compiler ne prouve rien : `ast.parse` accepte un module dont une
substitution a supprimé une variable. Ici chaque module est importé, son
`AnsibleModule` construit avec des arguments réels, et le SDK installé
interrogé sur chaque méthode que le module appelle.
"""

from __future__ import annotations

import ast
import importlib
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest
from ansible.module_utils import basic

REPO_ROOT = Path(__file__).resolve().parents[3]
COLLECTION = REPO_ROOT / "ansible_collections" / "stephrobert" / "exoscale"
MODULES = sorted(COLLECTION.glob("plugins/modules/*.py"))

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _import(path: Path) -> ModuleType:
    name = f"ansible_collections.stephrobert.exoscale.plugins.modules.{path.stem}"
    sys.modules.pop(name, None)
    return importlib.import_module(name)


def _arguments(module: ModuleType, **extra: object) -> None:
    payload = {
        "ANSIBLE_MODULE_ARGS": {"api_key": "k", "api_secret": "s", "zone": "ch-gva-2", **extra}
    }
    basic._ANSIBLE_ARGS = json.dumps(payload).encode()
    # ansible-core 2.19 et plus exige un profil de sérialisation à côté des
    # arguments ; `legacy` est celui que le débogage d'un module pose par défaut.
    basic._ANSIBLE_PROFILE = "legacy"


def _valeur_acceptable(entry: dict[str, object]) -> object:
    """Une valeur que l'argument_spec accepte : du type déclaré, ou un choix du contrat.

    `scale-deployment` exige `replicas`, un entier : la chaîne `x` que le test
    posait partout faisait refuser le module par ansible-core avant même
    l'appel, et le vert de ce test ne portait que sur les modules à options
    textuelles.
    """
    choices = entry.get("choices")
    if choices:
        return choices[0]
    return {"int": 1, "float": 1.0, "bool": True, "list": [], "dict": {}}.get(
        str(entry.get("type", "str")), "x"
    )


@pytest.fixture(autouse=True)
def _reset_ansible_args() -> None:
    basic._ANSIBLE_ARGS = None
    basic._ANSIBLE_PROFILE = None


def test_des_modules_ont_ete_generes() -> None:
    assert MODULES, "lancer `mise run generate` avant les tests de la collection"


@pytest.mark.parametrize("path", MODULES, ids=[p.stem for p in MODULES])
def test_le_module_simporte_et_son_argument_spec_est_accepte(path: Path) -> None:
    module = _import(path)
    extra: dict[str, object] = {}
    if hasattr(module.MODULE, "actions"):
        first = module.MODULE.actions[0]
        extra["action"] = first.name
        # Le sélecteur peut être absent : un singleton n'a aucun identifiant,
        # une ressource imbriquée en a deux, tous exigés par l'argument_spec.
        if module.MODULE.selector is not None:
            extra[module.MODULE.selector] = "11111111-2222-3333-4444-555555555555"
        for option in module.REQUIRED_IF:
            if option[1] == first.name:
                for name in option[2]:
                    extra.setdefault(name, _valeur_acceptable(module.ARGUMENT_SPEC[name]))
    # Ce que le module exige en dehors du sélecteur : `vpc_id` pour un
    # sous-réseau, par exemple.
    communs = {"api_key", "api_secret", "zone"}
    for name, entry in module.ARGUMENT_SPEC.items():
        if entry.get("required") and name not in extra and name not in communs:
            extra[name] = _valeur_acceptable(entry)
    _arguments(module, **extra)
    ansible_module = basic.AnsibleModule(
        argument_spec=module.ARGUMENT_SPEC,
        required_if=module.REQUIRED_IF,
        supports_check_mode=True,
    )
    assert ansible_module.params["zone"] == "ch-gva-2"


@pytest.mark.parametrize("path", MODULES, ids=[p.stem for p in MODULES])
def test_un_module_daction_refuse_une_action_sans_ses_options(path: Path) -> None:
    module = _import(path)
    if not hasattr(module.MODULE, "actions"):
        pytest.skip("module d'information")
    exigeantes = [item for item in module.REQUIRED_IF if item[2]]
    if not exigeantes:
        pytest.skip("aucune action n'exige d'option")
    _, action, _ = exigeantes[0]
    # Tout ce que le module exige au niveau du module (les identifiants
    # partagés, qu'il y en ait zéro, un ou deux), et rien de ce que l'action
    # exige : c'est ce manque-là que le test mesure.
    communs = {"api_key", "api_secret", "zone", "action"}
    identifiants = {
        name: _valeur_acceptable(entry)
        for name, entry in module.ARGUMENT_SPEC.items()
        if entry.get("required") and name not in communs
    }
    _arguments(module, action=action, **identifiants)
    with pytest.raises(SystemExit):
        basic.AnsibleModule(
            argument_spec=module.ARGUMENT_SPEC,
            required_if=module.REQUIRED_IF,
            supports_check_mode=True,
        )


@pytest.mark.parametrize("path", MODULES, ids=[p.stem for p in MODULES])
def test_le_sdk_installe_expose_chaque_operation_du_module(path: Path) -> None:
    """Le SDK est généré depuis le même contrat : s'il ne connaît pas une opération, il a dérivé."""
    from exoscale.api.v2 import Client

    module = _import(path)
    spec = module.MODULE
    operations = [
        op
        for op in (getattr(spec, "get_operation", None), getattr(spec, "list_operation", None))
        if op
    ]
    operations.extend(action.operation for action in getattr(spec, "actions", ()))
    for operation in operations:
        assert hasattr(Client, operation.method), (
            f"{operation.id} : {operation.method} absent du SDK"
        )


@pytest.mark.parametrize("path", MODULES, ids=[p.stem for p in MODULES])
def test_le_module_ne_porte_aucune_logique(path: Path) -> None:
    """Il ne définit que `main`, et `main` ne contient ni condition ni boucle."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    fonctions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    assert [f.name for f in fonctions] == ["main"]
    for node in ast.walk(fonctions[0]):
        assert not isinstance(node, (ast.If, ast.For, ast.While, ast.Try)), (
            "une décision s'est glissée"
        )


@pytest.mark.parametrize("path", MODULES, ids=[p.stem for p in MODULES])
def test_aucune_ligne_dun_module_ne_depasse_la_limite_de_sanity(path: Path) -> None:
    """`ansible-test sanity` refuse une ligne de plus de 160 caractères (pep8 E501).

    Mesuré sur les cinq versions d'ansible-core de la matrice : l'en-tête de
    `compute_instance_action` en faisait 240, et la sanity était rouge partout.
    Ce test le dit hors ligne, avant que la matrice ne le dise en CI.
    """
    trop_longues = [
        (numero, len(ligne))
        for numero, ligne in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1)
        if len(ligne) > 160
    ]
    assert trop_longues == [], f"{path.name} : lignes trop longues {trop_longues}"
