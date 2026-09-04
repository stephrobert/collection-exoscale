# collection-exoscale

Générateur de modules Ansible **Day-2** pour l'API v2 d'Exoscale, et la
collection `stephrobert.exoscale` qu'il produit.

> Terraform provisionne les ressources. Ansible exploite les ressources
> existantes.

Le générateur ne produit donc ni `create` ni `delete` : il produit des modules
d'information et d'action ponctuelle sur des ressources existantes.

## Pourquoi ce dépôt existe

Il n'existe aucune collection Ansible qui parle à l'API v2 d'Exoscale.
`ngine_io.exoscale` est dépréciée sur Galaxy (dernière version 1.1.0 du 25 août
2023), archivée sur GitHub (dernier commit le 21 novembre 2023), écrite à la
main, et ses trois modules visent des API v1 fermées le 1er mai 2024. Le
namespace `exoscale` existe sur Galaxy et il est vide.

Exoscale publie en revanche un contrat OpenAPI 3.0 complet et unique
(`https://openapi-v2.exoscale.com/source.json`) : 261 chemins, 374
opérations, 55 tags. C'est ce contrat qui est versionné ici, et c'est lui
qu'on mesure plutôt que de suivre l'API à la main.

## État

Squelette qui marche de bout en bout sur le produit `compute`. Mesuré par
`mise run report` et `mise run generate` :

```text
exoscale v2 : 374 opérations, 261 chemins, 14 produits recensés, 0 UNKNOWN dans chacun

compute v2 : 111 opérations découvertes, 70 asynchrones (réponse `operation`)
  INFO 35 · ACTION 18 · MANAGE 11 · LIFECYCLE 34 · IGNORE 13 · UNKNOWN 0
  Day-2 64 · AUTO 64 · classées pour génération automatique 100 % (64/64)

collection stephrobert.exoscale : 26 modules écrits, 13 écartés avec leur raison
  11 modules MANAGE sans renderer, 2 ressources imbriquées à deux sélecteurs
```

Les modules s'importent, leur `argument_spec` est accepté par ansible-core,
le runtime est mesuré par des doubles, chaque garde est falsifiée, et le SDK
installé expose chaque méthode qu'un module appelle. **Aucun module n'a encore
été joué contre le cloud réel.**

## Ce qui diffère de Scaleway, et pourquoi

Ce dépôt transpose l'architecture de `collection-scaleway`, pas ses fichiers.
Chaque écart est mesuré sur le contrat ; la table complète est dans
`CLAUDE.md`. Les trois plus structurants :

* **un seul document pour tous les produits.** `specs/exoscale/products.txt`
  indexe des tags racines, et `generator/source/` découpe le document ;
* **les actions sont portées par PUT, et `reset-*-field` par DELETE.** Les
  règles de Scaleway laissent 58 UNKNOWN sur 374 ; celles d'Exoscale en
  laissent 0 ;
* **203 écritures sur 374 sont asynchrones.** Le runtime attend l'objet
  `operation` jusqu'à `success` et le rend dans tous les cas.

## Commandes

```bash
mise install && mise run setup          # outillage épinglé, venv, dépendances verrouillées
mise run products                       # le document entier, produit par produit
mise run report                         # recensement, puis rapport strict de compute
mise run generate                       # les modules, dans ansible_collections/stephrobert/exoscale
mise run check                          # lint, types, tests, rapport, dérive des golden, falsification
mise run sync:api                       # retélécharger le contrat, puis lire le diff
```

## Arborescence

```text
generator/          le producteur : source, parser, ir, classifier, overrides, ansible, renderer, report
specs/exoscale/     le contrat versionné, et products.txt qui indexe des tags
ansible_collections/stephrobert/exoscale/   le livrable, à l'emplacement qu'Ansible impose
tests/fixtures/gadget/   un contrat de laboratoire qui reproduit les formes d'Exoscale
docs/architecture/  le générateur, et le contrat
```
