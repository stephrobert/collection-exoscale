# Architecture du générateur

Ce dépôt ne contient pas une collection Ansible écrite à la main : il contient
le générateur qui l'écrit, et les décisions qui transforment une API technique
en interface Ansible cohérente. La source des contrats et ses limites mesurées
sont dans [contrats-exoscale.md](contrats-exoscale.md).

## Le pipeline

```text
specs/exoscale/exoscale.v2.json         contrat versionné (OpenAPI 3.0), un pour tous les produits
        |
        v  generator/source/base.py     découpe par famille de tags (products.txt)
   SpecDocument                          le document, réduit aux chemins du produit
        |
        v  generator/parser/openapi.py
   ApiService                            IR canonique, sans Ansible ni SDK
        |
        v  generator/classifier/rules.py
   Classification                        INFO ACTION MANAGE WORKFLOW LIFECYCLE IGNORE UNKNOWN
        |
        v  generator/overrides/*.yml
   ProductPlan                           décision + module cible + raison
        |
        +--> generator/report/render.py  texte, JSON, Markdown
        |
        +--> generator/ansible/models.py modèle intermédiaire
                    |
                    v  generator/renderer + templates/
             plugins/modules/*.py
                    |
                    v  plugins/module_utils/exoscale.py
             exécution : SDK officiel, attente de l'opération, erreurs
```

## Les décisions structurantes

### 1. Un produit est une famille de tags, pas un fichier

Exoscale publie un document unique. `products.txt` indexe un tag racine par
ligne, et la source garde les opérations dont un tag remonte à cette racine.
`python -m generator products` recense le document entier pour que ce qui
n'est pas indexé reste compté.

### 2. La clé d'opération est stable

`compute.v2.Instance.start-instance` : produit, version, ressource, identifiant
du contrat. C'est la clé des overrides et celle du rapport.

### 3. La ressource se déduit du chemin

Premier et dernier segment porteur, une fois retirés les identifiants, le
suffixe `:verbe` et le segment d'action terminal. Mesuré : 165 ressources sur
le document entier, zéro `unknown`. Le cas où deux collections partagent un
nom (`vpc_route`) se corrige par override, et le rapport le montre.

### 4. Les règles de classification sont celles d'Exoscale

| verbe | méthode | classe |
|---|---|---|
| `get`, `list` | GET | INFO |
| `reveal` | GET | INFO, valeur sensible |
| `get`, `list` | POST | INFO |
| `create` | POST | LIFECYCLE |
| `delete` | DELETE | LIFECYCLE |
| `reset` | DELETE | ACTION |
| `update` | PUT, PATCH, POST | MANAGE |
| autre | PUT, POST | ACTION |
| autre | autre | UNKNOWN |

Les six règles de Scaleway laissaient 58 UNKNOWN sur 374 ; celles-ci en
laissent zéro sur chacun des 14 produits.

### 5. Une action est une opération

Un module d'action regroupe les opérations ponctuelles d'une ressource
(`compute_instance_action` : `start`, `stop`, `reboot`, `scale`,
`resize_disk`, `reset_field`, `reset_password`, `add_protection`,
`remove_protection`, `enable_tpm`, `revert_to_snapshot`). Le sélecteur est
l'identifiant de chemin commun à toutes ; un paramètre de chemin énuméré
(`{field}`) est une option ; ce que le contrat exige pour une action seule
devient un `required_if`.

### 6. L'asynchrone est un fait de l'IR

`ApiResponse.is_operation` porte le fait ; le plan compte les opérations
asynchrones ; le runtime attend l'opération quand `wait` est vrai et rend
l'objet dans tous les cas, avec son `state`.

### 7. La couverture nomme son dénominateur

```text
couverture Day-2 = (AUTO + OVERRIDE) / (INFO + ACTION + MANAGE + WORKFLOW)
```

Mesuré sur compute : 64 candidates Day-2 sur 111 opérations, 100 % classées
pour la génération automatique. Le compte rendu de génération publie à côté
la part portée par un module écrit, qui est plus basse tant que MANAGE n'a
pas de renderer.

## Deux golden, deux mesures différentes

* `tests/fixtures/compute/expected_ir.json` fige ce que le parser lit du
  contrat réel. Il bouge quand Exoscale bouge ;
* `tests/fixtures/gadget/expected_modules/` fige ce que le renderer écrit,
  depuis le contrat de laboratoire. Il ne doit pas bouger le jour où Exoscale
  ajoute une instance.

## Ce que le projet ne fait pas

Pas de `create`, pas de `delete`, pas d'attachement entre ressources, pas
d'abstraction multi-cloud. La frontière est posée une fois :

```text
Terraform provisionne les ressources. Ansible exploite les ressources existantes.
```
