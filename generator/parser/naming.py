"""Normalisation des noms entre le vocabulaire de l'API et celui d'Ansible.

Exoscale écrit tout en kebab-case : `operationId` (`start-instance`), segments
de chemin (`security-group`), propriétés (`disk-size`). Mesuré sur le contrat :
372 identifiants sur 374 portent un tiret, les deux autres sont d'un seul mot,
et aucun n'est en camelCase. Le découpage est donc simple, et il doit le
rester : un cas mal traité se corrige par un override, jamais par une
exception glissée ici.

Un nom d'option Ansible ne peut pas porter de tiret. `option_name` traduit
`disk-size` en `disk_size`, et la traduction n'est **pas** inversée : l'IR
garde le nom du contrat, et le module généré porte les deux côte à côte. Le
contrat contient 321 propriétés qui portent déjà un `_` (les réglages DBaaS,
`auth_url`, `allowed_domains`...), donc `disk_size` ne permet pas de retrouver
`disk-size` à coup sûr. Reconstituer serait deviner.
"""

from __future__ import annotations

#: Mots qui finissent par `s` sans être des pluriels, ou dont le pluriel est
#: irrégulier. Ceux mesurés dans les chemins du contrat, et rien de plus.
#:
#: Mesuré le 4 septembre 2026 sur les 24 mots de chemin qui finissent par `s` :
#: treize sont de vrais pluriels (`buckets`, `rules`, `rotations`, `types`...),
#: donc la singularisation reste nécessaire ; et quatre noms propres y
#: perdaient leur dernière lettre, `dbaas` (104 chemins) devenait `dbaa`,
#: `postgres` devenait `postgre`, `prometheus` `prometheu` et `thanos` `thano`.
#: Un nom de module s'écrit avec ces mots, et `dbaas_dbaa_postgre` n'est pas
#: un nom qu'un opérateur reconnaît.
IRREGULAR_SINGULARS: dict[str, str] = {
    "dns": "dns",
    "sos": "sos",
    "kms": "kms",
    "sks": "sks",
    "tls": "tls",
    "ssh": "ssh",
    "dbaas": "dbaas",
    "postgres": "postgres",
    "prometheus": "prometheus",
    "thanos": "thanos",
    "settings": "settings",
    "status": "status",
    "data": "data",
    "quotas": "quota",
}

#: Mots que la table ci-dessus déclare identiques au singulier et au pluriel.
INVARIABLE_WORDS: frozenset[str] = frozenset(
    word for word, singular in IRREGULAR_SINGULARS.items() if word == singular
)


def split_words(name: str) -> list[str]:
    """Découpe un identifiant kebab ou snake en mots, en minuscules.

    >>> split_words("start-instance")
    ['start', 'instance']
    >>> split_words("security_group_rules")
    ['security', 'group', 'rules']
    """
    return [chunk.lower() for chunk in name.replace("-", "_").split("_") if chunk]


def snake_case(name: str) -> str:
    """`security-group` -> `security_group`."""
    return "_".join(split_words(name))


def option_name(api_name: str) -> str:
    """Nom d'option Ansible d'un paramètre du contrat : `disk-size` -> `disk_size`.

    La fonction est totale et déterministe, mais pas injective : `auth_url` et
    un hypothétique `auth-url` donneraient le même nom. Le modèle de module
    refuse un tel conflit plutôt que de laisser deux paramètres se recouvrir.
    """
    return snake_case(api_name)


def singularize(word: str) -> str:
    """Singularise un mot anglais avec les seules règles dont l'IR a besoin.

    >>> singularize("rules"), singularize("policies"), singularize("addresses")
    ('rule', 'policy', 'address')
    >>> singularize("dns"), singularize("sks"), singularize("settings")
    ('dns', 'sks', 'settings')
    """
    lowered = word.lower()
    if lowered in IRREGULAR_SINGULARS:
        return IRREGULAR_SINGULARS[lowered]
    if lowered.endswith("ies") and len(lowered) > 4:
        return lowered[:-3] + "y"
    for suffix in ("sses", "shes", "ches", "xes", "zes"):
        if lowered.endswith(suffix):
            return lowered[:-2]
    if lowered.endswith("ss") or not lowered.endswith("s"):
        return lowered
    return lowered[:-1]


def singularize_phrase(phrase: str) -> str:
    """Singularise chaque mot d'une expression snake_case : `security_group_rules`."""
    return "_".join(singularize(word) for word in phrase.split("_") if word)


def pluralize(word: str) -> str:
    """Pluralise un mot anglais, avec les seules règles dont la doc a besoin.

    >>> pluralize("instance"), pluralize("policy"), pluralize("address")
    ('instances', 'policies', 'addresses')
    """
    lowered = word.lower()
    if lowered in INVARIABLE_WORDS:
        return lowered
    if lowered.endswith("y") and len(lowered) > 1 and lowered[-2] not in "aeiou":
        return lowered[:-1] + "ies"
    if lowered.endswith(("s", "sh", "ch", "x", "z")):
        return lowered + "es"
    return lowered + "s"


def pluralize_phrase(phrase: str) -> str:
    """Pluralise le dernier mot d'une expression snake_case, en mots séparés.

    `instance_type` -> `instance types` : c'est la tête de l'expression qui
    porte le nombre, et la documentation se lit en mots, pas en snake_case.
    """
    words = [word for word in phrase.split("_") if word]
    if not words:
        return phrase
    return " ".join([*words[:-1], pluralize(words[-1])])
