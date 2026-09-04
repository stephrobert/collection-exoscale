# Le contrat Exoscale : la source, ses limites, sa surveillance

Le générateur lit un document **OpenAPI 3.0** publié par Exoscale et versionné
dans `specs/exoscale/exoscale.v2.json`. Cette page dit d'où il vient, ce qu'il
porte, ce qu'il ne porte pas, et comment le dépôt s'aperçoit qu'il a bougé.
Toutes les mesures datent du 4 septembre 2026.

## La source

Un seul document pour tous les produits, servi à deux adresses :

| adresse | chemins | remarque |
|---|---|---|
| `https://openapi-v2.exoscale.com/source.json` | 261 | source de la documentation de référence, et copie embarquée par le SDK Python |
| `https://community.exoscale.com/reference/api/exoscale-openapi-spec.json` | 259 | sans `/ai/api-key/{id}/reveal` ni `/ai/api-key/{id}/rotate` |

`mise run sync:api` télécharge la première, octet pour octet. `openapi: 3.0.0`,
`info.version: 2.0.0`, serveur `https://api-{zone}.exoscale.com/v2` avec huit
zones énumérées.

## Ce que le document porte

374 opérations, 303 schémas, 55 tags dont 12 parents. Pour chaque opération :
un `operationId` en kebab-case (`start-instance`), des tags qui disent le
produit, des paramètres de chemin typés pour la plupart, un corps de requête
avec `required` sur 64 corps sur 142, et une réponse de succès.

Trois formes de réponse : 81 GET répondent par une référence (la ressource),
50 par un objet inline à une propriété (une enveloppe de liste ou d'objet), 2
par un tableau nu. **203 écritures répondent par le schéma `operation`** :
l'API accepte le travail et rend son identifiant, et le résultat se lit en
interrogeant `get-operation` jusqu'à `success`, `failure` ou `timeout`.

## Ce que le document ne porte pas

* **aucune pagination.** Aucun paramètre `page`, `limit`, `offset` ni
  `cursor`. Le parser le signale une fois par produit ;
* **44 paramètres de chemin sans schéma** (`{name}`, `{service-name}`,
  `{username}`). Le type est inconnu et se tranche par un override `type` ;
* **3 tags employés sans être déclarés** (`ccm`, `organization`, `quotas`) et
  **2 opérations sans tag** (`get-impact-estimate`, `get-impact-report`). Le
  recensement les nomme ;
* **aucune déclaration d'authentification** (`securitySchemes` est vide). Le
  schéma `EXO2-HMAC-SHA256` est documenté à part
  (`https://openapi-v2.exoscale.com/topic/topic-api-request-signature`) et
  calculé par le SDK ;
* **aucun état attendu après une action.** `operation.state == success` dit
  que le travail est fini, pas que l'instance est `running`.

## Deux rôles qui ne se confondent jamais

| rôle | qui le tient |
|---|---|
| décrire l'API pour la génération | le document versionné dans `specs/exoscale/` |
| appeler l'API à l'exécution | le SDK Python officiel `exoscale`, généré depuis le même document |

Le SDK embarque sa propre copie du contrat et en dérive ses méthodes
(`operationId.replace("-", "_")`). Un test exige que le SDK installé expose
chaque méthode qu'un module généré appelle : quand les deux copies divergent,
c'est là que ça se voit.

## Reproduire les mesures

```bash
curl -sL -o /dev/null -w '%{http_code} %{size_download}\n' https://openapi-v2.exoscale.com/source.json
mise run sync:api
python -m generator products --classify
python -m generator inspect compute
python -m generator report compute --strict
```
