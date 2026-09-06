# Le stockage : un volume Block Storage et son instantané.
#
# Block Storage est une API distincte de celle du disque d'instance, et ses
# modules le sont aussi : `block_storage_volume_info`, `block_storage_volume_action`
# et `block_storage_snapshot_info` n'ont de cible que par ces deux ressources.
#
# **Ce que la stack ne crée pas, et pourquoi.** La première version bâtissait
# aussi un instantané du disque d'une machine applicative, par le SDK. Le
# fournisseur Terraform 0.71.0 n'a aucune ressource pour l'instantané d'une
# instance (mesuré sur la liste des ressources du registre le 5 septembre
# 2026), et la collection n'en crée pas non plus : `create-snapshot` est
# LIFECYCLE, périmètre Terraform. Les modules d'instantané d'instance perdent
# donc leur cible, et c'est écrit dans `scripts/example_coverage.py` avec cette
# mesure, plutôt que bricolé par un `local-exec` qui rouvrirait une seconde
# façon de bâtir la plateforme.

resource "exoscale_block_storage_volume" "donnees" {
  zone   = var.zone
  name   = "${local.prefixe}-data"
  size   = 10
  labels = local.labels
}

resource "exoscale_block_storage_volume_snapshot" "donnees" {
  zone   = var.zone
  name   = "${local.prefixe}-data-snap"
  labels = local.labels

  volume = {
    id = exoscale_block_storage_volume.donnees.id
  }
}
