# Instructions Claude Code : collection-exoscale

Ce dépôt produit une **collection Ansible Day-2 pour Exoscale**, et surtout le
générateur qui l'écrit. Le code généré n'est pas le produit : le produit est le
contrat versionné, les règles de classification, et les quelques overrides
explicites qui transforment une API technique en interface Ansible cohérente.

Il transpose l'architecture de `collection-scaleway`, pas ses fichiers.
Chaque écart avec Scaleway est mesuré sur le contrat d'Exoscale, et la mesure
est écrite à côté de la décision qu'elle justifie.

## Objectif majeur (l'étoile polaire)

**Un module généré doit être celui qu'un opérateur aurait écrit à la main, en
mieux tenu.** Un test unitaire vert ne prouve rien : la preuve est qu'un
playbook réel passe, et qu'un utilisateur comprend le module sans lire l'API
Exoscale.

Le corollaire, qui tranche toutes les ambiguïtés de design :

```text
Terraform provisionne les ressources. Ansible exploite les ressources existantes.
```

Une opération qui crée, supprime ou relie des ressources n'a pas sa place ici,
même si le générateur sait la produire.

## L'angle différenciant (ne jamais le perdre)

**On ne suit pas l'API à la main, on la mesure.** Il n'existe aucune collection
Ansible qui parle à l'API v2 d'Exoscale : `ngine_io.exoscale` est dépréciée sur
Galaxy, archivée sur GitHub depuis novembre 2023, écrite à la main, et ses
trois modules visent des API v1 fermées le 1er mai 2024.

Trois mécanismes rendent la dérive visible. Ils priment sur toute autre
considération de design :

1. **Le contrat est versionné** dans `specs/exoscale/exoscale.v2.json`, octet
   pour octet tel qu'Exoscale le publie. Une évolution arrive comme un diff.
2. **Le golden IR** (`tests/fixtures/compute/expected_ir.json`) fait échouer
   la CI dès qu'une opération, un paramètre ou un enum bouge.
3. **Le rapport en mode strict** sort en code 2 sur toute opération non classée
   et tout override orphelin.

## Ce qu'Exoscale fait autrement que Scaleway, mesuré

Ces faits sont ceux du contrat du 4 septembre 2026 (261 chemins, 374
opérations, 303 schémas, 55 tags). Chacun a changé le code.

| fait mesuré | conséquence dans le code |
|---|---|
| **un seul document pour 14 produits** ; le tag dit le produit (`instance` a pour parent `compute`) | `products.txt` indexe des **tags racines**, `generator/source/` découpe le document par famille de tags ; `python -m generator products` recense ce qui n'est pas indexé |
| 3 tags employés sans être déclarés (`ccm`, `organization`, `quotas`), 2 opérations sans aucun tag (`get-impact-estimate`, `get-impact-report`) | le recensement les nomme ; elles ne sont dans aucun produit, et ce n'est pas silencieux |
| la zone est dans l'hôte (`api-{zone}.exoscale.com`), pas dans le chemin | pas de `Scope` dans l'IR ; `zone` est un paramètre commun du runtime ; les huit zones sont sur `ApiService.zones` |
| **les actions sont portées par PUT** (52 des 89 PUT : `start-instance`, `scale-instance`, `rotate-sks-*`) et **`reset-*-field` par DELETE** | les règles de Scaleway laissent **58 UNKNOWN sur 374** ; celles de `generator/classifier/rules.py` en laissent **0** : le verbe de l'`operationId` tranche, la méthode confirme |
| pas de préfixe produit/version dans le chemin, verbe personnalisé en suffixe `:start` (34 chemins), segment d'action terminal (`/maintenance/start`) | la dérivation de ressource de Scaleway rend `unknown` sur 249 chemins ; celle de `derive_resource` en rend 0 et nomme 165 ressources |
| **203 écritures sur 374 répondent par un objet `operation` asynchrone** (70 sur 111 pour compute) | l'IR porte `is_operation`, le rapport compte les asynchrones, le runtime attend `success` quand `wait` est vrai et rend l'opération dans tous les cas |
| `required` déclaré sur 64 corps sur 142 | le mapping s'en sert ; dans un module d'action, une obligation propre à une action devient un `required_if`, jamais un `required` global |
| tout est en kebab-case, jusqu'aux propriétés (`disk-size`), et 321 propriétés portent déjà un `_` | `option_name` traduit vers `disk_size` et **n'inverse jamais** : le module garde le nom du contrat à côté de l'option, et le runtime envoie celui du contrat |
| **aucune pagination** : ni `page`, ni `limit`, ni `cursor` sur aucune opération | le parser ne l'invente pas ; il le signale dans les limites, une fois par produit |
| 44 paramètres de chemin sans schéma (`{name}`, `{service-name}`, `{username}`) | type `unknown`, module écarté avec sa raison, et un override `type` avec sa raison pour trancher |
| `readOnly` sur 169 propriétés, `nullable` sur 69, aucun `oneOf` | `read_only` dans l'IR et jamais dans un `argument_spec` ; `nullable` ignoré ; une composition lèverait un type inconnu |
| une action est une **opération**, pas une valeur d'enum (`start-instance`, `stop-instance`) | un module d'action regroupe les opérations d'une ressource ; le nom de l'action est calculé (`resize-instance-disk` -> `resize_disk`) |
| un paramètre de chemin énuméré (`{field}` vaut `labels` ou `user-data`) | ce n'est pas un sélecteur, c'est une option de l'action ; sans cette règle, quatre ressources n'avaient pas de module d'action |
| le SDK Python officiel est **généré depuis ce même contrat** (`operationId.replace("-", "_")`) et embarque sa copie | le runtime appelle le SDK par ce nom, et un test exige que le SDK installé expose chaque méthode qu'un module appelle |

## Architecture

```text
LE PRODUCTEUR, à la racine
generator/source/       lecture du contrat versionné, découpage par tag, jamais du réseau
generator/parser/       OpenAPI 3.0 -> IR canonique ; traduit, ne décide rien
generator/ir/           dataclasses gelées, sérialisation déterministe
generator/classifier/   les règles d'Exoscale ; ce qui reste est UNKNOWN
generator/overrides/    les décisions humaines, chacune avec sa raison
generator/ansible/      noms de modules, types, traduction kebab/snake, modèle du module
generator/renderer/     Jinja2, rendu seul
generator/report/       texte, JSON, Markdown
scripts/                sync, rapport, golden, dérive, sanity, archive, release, compteurs, falsification
specs/exoscale/         le contrat, et products.txt qui indexe des tags
tests/fixtures/gadget/  un contrat de laboratoire qui reproduit les formes d'Exoscale
docs/                   publié, en anglais : le générateur, le contrat, Scorecard
.github/                onze workflows, CODEOWNERS, dependabot, le ruleset de main

LE LIVRABLE, à l'emplacement qu'Ansible impose
ansible_collections/stephrobert/exoscale/
    galaxy.yml          l'identité, seule source du namespace
    plugins/module_utils/exoscale.py   client SDK, appel, attente de l'opération, erreurs
    plugins/modules/    les modules générés
    plugins/doc_fragments/  les paramètres communs, et le fragment `wait`
    meta/               requires_ansible mesuré, et les métadonnées d'EE
    changelogs/         les fragments, et le changelog qu'ils composent
```

**Aucun nom en dur dans un contrôle.** Chez scaleway, quatre contrôles en une
journée ont survécu au renommage de ce qu'ils contrôlaient : le bloc du README,
le contrôle de couverture, son test, le contrôle de l'archive. Ici, `package.py`
lit `plugins/` sur le disque, `readme_counters.py` lit l'index des produits, les
modules et les tags du contrat. Ne coder aucun nom de module, de plugin ni de
produit dans un contrôle.

**Pourquoi le chemin et `galaxy.yml` déclarent tous deux le namespace.**
Ansible lit les deux, on ne peut en supprimer aucun, alors `load_collection`
exige qu'ils concordent.

## Règles non négociables

1. **Aucune opération ne disparaît.** Une opération qu'aucune règle ne tranche
   est `UNKNOWN` et fait échouer `report --strict`. Une opération hors des
   produits indexés est comptée par `products`, jamais oubliée.
2. **Un override porte une raison.** Le chargeur refuse un changement de
   classification, un renommage, un typage ou un masquage sans `reason`, et
   refuse un champ inconnu.
3. **Le générateur ne devine pas.** Un type absent lève plutôt que de devenir
   un `str` ; une pagination absente n'est pas inventée ; un nom d'option
   n'est jamais retraduit vers le contrat.
4. **Le parser ne décide pas, le classifieur ne nomme pas, la source ne
   traduit pas.** Chaque étape a une responsabilité.
5. **Aucune logique dans un template.**
6. **La génération est déterministe.** Même contrat, mêmes fichiers.
7. **`EXOSCALE_API_URL` reste honoré de bout en bout**, pour un émulateur.
8. **Pas de `git push` sans accord explicite.** Commits locaux.
9. **Codes de sortie stables** : `0`, `1` erreur, `2` non trié ou orphelin.
10. **Un module ne ment pas sur `changed`.** Une écriture est asynchrone ; le
    module attend l'opération, ou dit qu'il ne l'a pas attendue.

## La métrique ne se maquille pas

```text
couverture Day-2 = (AUTO + OVERRIDE) / (INFO + ACTION + MANAGE + WORKFLOW)
```

Mesuré sur compute : 111 opérations, 64 candidates Day-2, 100 % classées
pour la génération automatique, 34 LIFECYCLE et 13 IGNORE écartées avec leur
raison. Ce chiffre dit que 64 opérations sur 64 sont classées, pas qu'un
module les porte : le compte rendu de génération publie les deux ratios, et
les 11 MANAGE n'ont pas encore de renderer.

## Un commentaire n'est pas un contrôle

Une garde dont la suppression laisse tous les tests verts est un commentaire.
`mise run falsify` neutralise chaque garde déclarée dans
`tests/falsify/specs.json` dans une copie hors dépôt et exige que le test nommé
échoue. À lancer après tout ajout de garde.

## Les pièges propres à Exoscale

* **Deux ressources pour un nom.** `/vpc/{vpc-id}/route` et
  `/vpc/{vpc-id}/subnet/{subnet-id}/route` donnent tous deux `vpc_route` à la
  règle « premier et dernier segment ». C'est l'inverse du piège de Scaleway,
  et le rapport le montre parce qu'il affiche la ressource de chaque
  opération. Corrigé par override, pas par une règle qui regarderait le
  milieu du chemin.
* **Un segment d'action à plusieurs mots.** `/kms-key/{id}/schedule-deletion`
  et `/sks-cluster/{id}/rotate-ccm-credentials` finissent par un segment qui
  nomme l'action en plusieurs mots ; une règle qui ne reconnaissait qu'un
  segment **égal** au verbe en faisait des ressources, donc douze modules
  fantômes (`kms_key_schedule_deletion_action`). La règle regarde le premier
  mot du segment. Mesuré en indexant les treize autres produits, et vu parce
  que deux overrides sont devenus orphelins.
* **Le générateur écrit sans retirer.** Les douze fantômes sont restés sur le
  disque après la correction, dans l'archive et dans le README.
  `scripts/generate_all.py` retire les modules de la génération précédente
  avant de régénérer, et le dit.
* **Un identifiant qui change de nom.** `revert-instance-to-snapshot` dit
  `{instance-id}` là où treize actions disent `{id}`, et son corps porte un
  `id` qui est celui du snapshot. Le champ d'override `option` existe pour ça.
* **Deux sources pour le même contrat.** `openapi-v2.exoscale.com/source.json`
  a deux chemins de plus que `community.exoscale.com/reference/api/`. C'est la
  première qui est versionnée, et `sync:api` le dit.
* **`wait` n'est pas l'état de la ressource.** L'opération à `success` dit
  que le travail est fini, pas que l'instance est `running`. L'état attendu
  se déclare dans un override `wait`, et le runtime ne le vérifie pas encore.

## Avant de pousser

```bash
mise run check     # lint, types, tests, recensement et rapport strict, dérive des golden,
                   # fragments de changelog, falsification, compteurs des README, archive
```

`check` porte tout ce que le job Générateur et le job Archive de la CI
portent : c'est la promesse de son nom, et l'archive y est parce qu'un défaut
a voyagé jusqu'en CI chez scaleway faute d'y être.

| ce que le changement touche | à lancer en plus | ce que ça prouve |
|---|---|---|
| une règle de classification, une règle de nommage | `mise run report` et lire le diff | que la décision change là où on croit |
| une garde, une validation, un refus | `mise run falsify` | que le test mord sans le correctif |
| le parser, l'IR | `mise run golden:update` puis lire le diff | ce que le changement fait vraiment aux opérations |
| un module généré, un template, le runtime | `mise run sanity` | qu'Ansible accepte le fichier produit, sur la version du verrou ; la matrice de CI fait les autres |
| le contrat | `mise run sync:api`, `mise run drift`, `mise run check` | ce qui a bougé, produit par produit, indexé ou non |
| un workflow, une action, `.github/` | `mise run security` | qu'actionlint, zizmor et poutine acceptent le pipeline |
| `pyproject.toml` | `mise run lock` puis lire le diff | quelle dépendance apparaît vraiment, et sous quelle empreinte |
| `meta/runtime.yml` | remesurer sanity sur chaque version de la matrice | que la borne est mesurée, pas estimée |

## Ce qui n'est pas encore prouvé

Les modules s'importent, leur `argument_spec` est accepté par Ansible, le
runtime est mesuré par des doubles, le SDK installé expose chaque méthode
appelée, `ansible-test sanity` passe de 2.17 à 2.21 et l'archive s'installe
et répond à `ansible-doc`. **Aucun module n'a encore été joué contre le cloud
réel, et il n'existe pas d'émulateur de l'API Exoscale.** Le dire vaut mieux
qu'un vert qui ne mesure pas ça.

## Le témoin du mode strict

`report --strict` sort en 0 sur un dépôt sain comme sur un mode strict cassé :
un contrôle qui cherche une absence est indiscernable d'un contrôle qui n'a
rien regardé. `tests/unit/generator/test_cli.py` fabrique un contrat que
personne ne sait classer et exige le code 2, et la mutation
`mode-strict-temoin` prouve que ce test mord.

## Langue

La frontière est **ce qui est publié**, pas le fichier qui le produit.

| quoi | langue |
|---|---|
| les deux README, `docs/`, `SECURITY.md`, `galaxy.yml`, les fragments de changelog | **anglais** |
| ce que `DOCUMENTATION`, `EXAMPLES` et `RETURN` portent | **anglais**, il vient du contrat |
| le code, les commentaires, les docstrings | **français**, avec les accents |
| les noms de tests, les raisons de mutation, les raisons d'override | **français** |
| la sortie des programmes : rapports, messages d'erreur, falsification | **français** |
| les workflows, leurs commentaires et les noms de jobs | **français** |
| les messages de commit | **français** |

Les identifiants Python, les noms de modules Ansible et le vocabulaire de l'API
restent en anglais partout : ce sont des noms propres, pas de la prose.

**Conséquence pour les blocs dérivés.** `scripts/readme_counters.py` écrit
dans deux fichiers publiés : sa sortie est en anglais, point décimal des
pourcentages compris, alors que son code et ses messages d'erreur restent en
français.

Ne jamais utiliser le tiret cadratin, dans les deux langues.
