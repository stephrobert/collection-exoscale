# stephrobert.exoscale

Modules Ansible **Day-2** pour l'API v2 d'Exoscale, produits par le générateur
du dépôt qui héberge cette collection.

> Terraform provisionne les ressources. Ansible exploite les ressources
> existantes.

Les modules d'information lisent, les modules d'action déclenchent une
opération sur une ressource existante et attendent sa fin. Aucun module ne
crée, ne supprime ni ne relie de ressources.

## Authentification

Chaque module accepte `api_key`, `api_secret` et `zone`, avec repli sur
`EXOSCALE_API_KEY`, `EXOSCALE_API_SECRET` et `EXOSCALE_ZONE`. La signature
`EXO2-HMAC-SHA256` est calculée par le SDK officiel `exoscale`, qui est la
seule dépendance d'exécution.

## État

Squelette : les modules sont générés et s'importent, leur `argument_spec` est
accepté par Ansible, et le SDK installé expose chaque méthode qu'ils appellent.
Ils n'ont pas encore été joués contre le cloud réel.
