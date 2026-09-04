# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Le runtime commun des modules générés : client, appel, attente, erreurs.

Un module généré ne contient aucune logique : il déclare ce qu'il appelle
(`InfoModule`, `ActionModule`) et confie l'exécution à ce fichier.

Cinq décisions, et ce qu'elles coûtent :

1. **Le SDK officiel est le client d'exécution.** `exoscale.api.v2.Client`
   construit ses méthodes depuis le même contrat que ce générateur
   (`operationId.replace("-", "_")`) et signe les requêtes
   (`EXO2-HMAC-SHA256`). Le générateur ne devine aucun nom : une garde de test
   vérifie que le SDK installé expose chaque méthode qu'un module appelle ;
2. **Les arguments partent sous le nom du contrat.** Le module porte, pour
   chaque option, le nom du contrat (`disk-size`) à côté du nom Ansible
   (`disk_size`). Le SDK veut `disk_size` en mot-clé et envoie `disk-size` :
   c'est lui qui normalise, depuis sa propre copie du contrat ;
3. **Une écriture est asynchrone, et le module l'attend.** L'API rend un objet
   `operation` ; rendre `changed` à cet instant serait mentir. Quand `wait`
   est vrai (le défaut), le runtime interroge l'opération jusqu'à `success`,
   et échoue sur `failure` ou `timeout` avec la raison de l'API ;
4. **L'URL de l'API reste honorée de bout en bout.** `api_url` et
   `EXOSCALE_API_URL` remplacent l'hôte construit depuis la zone, ce qui rend
   possible un émulateur local sans identifiants réels ;
5. **Une erreur dit quoi diagnostiquer.** Elle porte l'opération et le message
   du SDK, sans jamais recopier ce que le module a envoyé.

Ce que ce runtime ne porte pas encore : la comparaison et le diff d'un module
MANAGE, et l'état de ressource attendu après une action (`expected_state`),
déclaré par les overrides mais pas encore vérifié.
"""

from __future__ import annotations

import os
import time
import traceback
from collections import namedtuple

from ansible.module_utils.basic import env_fallback, missing_required_lib

try:
    from exoscale.api.exceptions import ExoscaleAPIException
    from exoscale.api.v2 import Client

    HAS_EXOSCALE = True
    EXOSCALE_IMPORT_ERROR = None
except ImportError:
    HAS_EXOSCALE = False
    EXOSCALE_IMPORT_ERROR = traceback.format_exc()
    Client = None  # type: ignore[assignment,misc]

    class ExoscaleAPIException(Exception):  # type: ignore[no-redef]
        """Doublure, le temps que le SDK manque : le module échoue avant de l'utiliser."""


#: Ce qu'un module généré déclare pour une opération. Chaque dictionnaire va
#: de l'option Ansible au nom du contrat.
Operation = namedtuple(
    "Operation",
    [
        "id",
        "method",
        "path_params",
        "query_params",
        "body_params",
        "payload_field",
        "is_list",
        "is_async",
    ],
    defaults=({}, {}, None, False, False),
)

#: Une action d'un module d'action, l'état attendu une fois finie, et si elle
#: agit même quand cet état est déjà atteint (`reboot` vise `running` et doit
#: redémarrer une machine qui tourne).
Action = namedtuple(
    "Action", ["name", "operation", "expected_state", "always"], defaults=(None, False)
)

#: Un module d'information : une lecture unitaire, une liste, et le sélecteur
#: qui bascule de l'une à l'autre.
InfoModule = namedtuple(
    "InfoModule",
    ["resource", "get_operation", "list_operation", "selector"],
    defaults=(None, None, None),
)

#: Un module d'action : le sélecteur commun, les actions qu'il regroupe, et
#: quand un état est attendu, le champ qui le porte et la lecture qui le rend.
ActionModule = namedtuple(
    "ActionModule",
    ["resource", "selector", "actions", "state_field", "read_operation"],
    defaults=(None, None),
)

DEFAULT_WAIT_TIMEOUT = 600

#: Intervalle entre deux lectures de l'état, en secondes.
POLL_INTERVAL = 2

#: Remplaçable par un test : attendre pour de vrai n'y prouve rien.
_sleep = time.sleep


def exoscale_argument_spec():
    """Les paramètres communs : identifiants, zone, URL."""
    return {
        "api_key": {
            "type": "str",
            "required": True,
            "no_log": False,
            "fallback": (env_fallback, ["EXOSCALE_API_KEY"]),
        },
        "api_secret": {
            "type": "str",
            "required": True,
            "no_log": True,
            "fallback": (env_fallback, ["EXOSCALE_API_SECRET"]),
        },
        "zone": {
            "type": "str",
            "required": True,
            "fallback": (env_fallback, ["EXOSCALE_ZONE"]),
        },
        "api_url": {
            "type": "str",
            "fallback": (env_fallback, ["EXOSCALE_API_URL"]),
        },
    }


def exoscale_waitable_argument_spec():
    """Les paramètres d'attente d'une opération asynchrone."""
    return {
        "wait": {"type": "bool", "default": True},
        "wait_timeout": {"type": "int", "default": DEFAULT_WAIT_TIMEOUT},
    }


def build_client(module):
    """Construit l'unique client, dans l'ordre : paramètres, puis environnement."""
    if not HAS_EXOSCALE:
        module.fail_json(msg=missing_required_lib("exoscale"), exception=EXOSCALE_IMPORT_ERROR)
    params = module.params
    api_url = params.get("api_url") or os.environ.get("EXOSCALE_API_URL")
    if api_url:
        return Client(params["api_key"], params["api_secret"], url=api_url)
    return Client(params["api_key"], params["api_secret"], zone=params["zone"])


def arguments_for(module, operation):
    """Les mots-clés que le SDK attend, depuis les options renseignées.

    La clé envoyée au SDK est le nom du contrat normalisé (`disk-size` ->
    `disk_size`), jamais le nom de l'option : les deux coïncident presque
    toujours, et c'est le presque qui fait la différence (`instance-id` porté
    par l'option `id`).
    """
    kwargs = {}
    for mapping in (operation.path_params, operation.query_params, operation.body_params):
        for option, api_name in mapping.items():
            value = module.params.get(option)
            if value is not None:
                kwargs[api_name.replace("-", "_")] = value
    return kwargs


def call(module, client, operation, kwargs):
    """Appelle une opération du SDK, et traduit son échec en `fail_json`."""
    method = getattr(client, operation.method, None)
    if method is None:
        module.fail_json(
            msg="the installed exoscale SDK does not expose this operation",
            operation=operation.id,
            sdk_method=operation.method,
        )
    try:
        return method(**kwargs)
    except ExoscaleAPIException as error:
        module.fail_json(msg=str(error), operation=operation.id)
    except TypeError as error:
        module.fail_json(msg=f"argument refused by the SDK: {error}", operation=operation.id)


def run_info_module(module, spec):
    """Lit une ressource par son sélecteur, ou les liste."""
    client = build_client(module)
    selected = spec.selector is not None and module.params.get(spec.selector) is not None
    if selected and spec.get_operation is not None:
        operation = spec.get_operation
    elif spec.list_operation is not None:
        operation = spec.list_operation
    elif spec.get_operation is not None:
        operation = spec.get_operation
    else:
        module.fail_json(msg="this module declares no operation")
        return

    result = call(module, client, operation, arguments_for(module, operation))
    payload = result
    if operation.payload_field is not None and isinstance(result, dict):
        payload = result.get(operation.payload_field)
    key = _plural(spec.resource) if operation.is_list else spec.resource
    module.exit_json(changed=False, **{key: payload})


def read_state(module, client, spec):
    """L'état courant de la ressource, lu par l'opération de lecture du module.

    `None` quand la lecture ne rend pas le champ : le module ne devine pas un
    état, il dit qu'il ne l'a pas lu.
    """
    read = spec.read_operation
    payload = call(module, client, read, arguments_for(module, read))
    if read.payload_field is not None and isinstance(payload, dict):
        payload = payload.get(read.payload_field)
    if not isinstance(payload, dict) or payload.get(spec.state_field) is None:
        return None
    return str(payload[spec.state_field])


def poll_state(module, client, spec, expected, timeout):
    """Lit la ressource jusqu'à l'état attendu, et échoue en disant l'état lu.

    `operation.state == success` dit que le travail est fini, pas que la
    ressource est dans l'état visé. Cette boucle est ce qui sépare « l'API a
    accepté » de « la machine tourne ». L'échec dit `changed=True` : l'action a
    été envoyée et acceptée, et un playbook rejoué doit le savoir.
    """
    deadline = time.monotonic() + timeout
    state = read_state(module, client, spec)
    while state != expected:
        if time.monotonic() >= deadline:
            module.fail_json(
                changed=True,
                msg=(
                    f"the operation succeeded, but the {spec.resource} is "
                    f"{state!r} after {timeout} seconds, expected {expected!r}"
                ),
                operation=None,
                **{spec.state_field: state},
            )
        _sleep(POLL_INTERVAL)
        state = read_state(module, client, spec)
    return state


def run_action_module(module, spec):
    """Déclenche une action, attend l'opération, puis l'état attendu s'il est déclaré.

    Quatre choses qu'un module d'action doit tenir, et que celui-ci tient :

    * **en check mode, ne rien envoyer** ;
    * **ne rien envoyer non plus quand l'état visé est déjà là**, et le dire
      par `changed=False` : `start` sur une machine qui tourne n'a rien à
      faire. Sauf pour une action déclarée `always`, comme `reboot`, qui vise
      `running` et doit redémarrer une machine qui tourne ;
    * **`changed` est vrai dès que l'API a accepté** : tout échec ultérieur, de
      l'attente de l'opération ou de l'état, le dit ;
    * **attendre l'état, si on sait quoi attendre.** L'état visé vient d'un
      override, jamais du contrat, qui ne le dit pas.
    """
    wanted = module.params["action"]
    action = next((item for item in spec.actions if item.name == wanted), None)
    if action is None:
        module.fail_json(msg=f"unknown action {wanted!r}")
        return
    operation = action.operation
    kwargs = arguments_for(module, operation)
    wait = bool(module.params.get("wait", True))
    timeout = module.params.get("wait_timeout") or DEFAULT_WAIT_TIMEOUT

    # La vérification d'état demande trois choses que le générateur ne fournit
    # qu'ensemble : une lecture de la ressource, le champ qui porte l'état, et
    # l'état attendu de cette action.
    verifies = (
        wait
        and spec.read_operation is not None
        and spec.state_field is not None
        and action.expected_state is not None
    )

    if module.check_mode:
        module.exit_json(changed=True, operation=None, msg="check mode: the action was not sent")

    client = build_client(module)

    if verifies and not action.always:
        current = read_state(module, client, spec)
        if current == action.expected_state:
            module.exit_json(
                changed=False,
                operation=None,
                msg=f"the {spec.resource} already is {current!r}: nothing was sent",
                **{spec.state_field: current},
            )

    result = call(module, client, operation, kwargs)

    if not operation.is_async:
        # Une action synchrone rend sa réponse, pas une opération : `enable-kms-key`
        # rend `success-response`, `resize-block-storage-volume` rend le volume.
        # La ranger sous `operation` ferait chercher un `state` qui n'existe pas.
        module.exit_json(changed=True, result=result)

    if operation.is_async and isinstance(result, dict) and module.params.get("wait", True):
        try:
            result = client.wait(result["id"], max_wait_time=timeout)
        except ExoscaleAPIException as error:
            # À partir d'ici l'API a **accepté** : la ressource a changé, et un
            # `fail_json` sans `changed` ferait croire à un playbook rejoué qu'il
            # n'a rien fait, alors que la machine a bougé.
            module.fail_json(
                changed=True, msg=str(error), operation=operation.id, operation_id=result.get("id")
            )

    extra = {}
    if verifies:
        extra[spec.state_field] = poll_state(module, client, spec, action.expected_state, timeout)
    module.exit_json(changed=True, operation=result, **extra)


def _plural(resource):
    """`instance_type` -> `instance_types`, pour la clé de retour d'une liste."""
    words = resource.split("_")
    last = words[-1]
    if last.endswith("y") and len(last) > 1 and last[-2] not in "aeiou":
        last = last[:-1] + "ies"
    elif last.endswith(("s", "sh", "ch", "x", "z")):
        last = last + "es"
    else:
        last = last + "s"
    return "_".join(words[:-1] + [last])
