# Les machines, et la seule adresse publique de la plateforme.
#
# Trois étages : un bastion qui porte la seule adresse élastique, un tier web
# et un tier applicatif sans aucune adresse publique. Ce choix n'est pas
# décoratif : c'est lui qui fait de l'exemple une preuve du plugin
# d'inventaire. Quatre machines sur cinq ne sont joignables que par le bail que
# leur réseau privé leur a donné, et c'est cette adresse-là que le plugin doit
# trouver.

resource "exoscale_ssh_key" "exemple" {
  name       = "${local.prefixe}-cle"
  public_key = var.ssh_public_key
}

# Le modèle est résolu par son nom, avec le filtre de visibilité écrit plutôt
# que laissé à son défaut : c'est ce paramètre que feint a laissé tomber un
# jour (feint#271), et l'écrire est ce qui garde ce chemin de lecture sous un
# vrai client.
data "exoscale_template" "ubuntu" {
  zone       = var.zone
  name       = var.template
  visibility = "public"
}

# Le groupe d'anti-affinité étale les machines applicatives sur des
# hyperviseurs distincts : perdre une lame ne doit pas emporter le tier entier.
resource "exoscale_anti_affinity_group" "app" {
  name        = "${local.prefixe}-app"
  description = "le tier applicatif de ${local.prefixe}, une machine par lame"
}

# --- le bastion, seule adresse publique -----------------------------------

# L'adresse porte le préfixe dans sa description, et pas seulement dans ses
# labels : feint ne rendait pas les labels d'une adresse, et la première
# destruction en a laissé une derrière elle. C'est le contrôle de résidu qui
# l'a dit, et c'est ce qui vaut à cette ressource deux marqueurs.
resource "exoscale_elastic_ip" "bastion" {
  zone        = var.zone
  description = "${local.prefixe}-bastion"
  labels      = local.labels
}

resource "exoscale_compute_instance" "bastion" {
  zone        = var.zone
  name        = "${local.prefixe}-bastion"
  template_id = data.exoscale_template.ubuntu.id
  type        = var.instance_type
  disk_size   = 10
  ssh_keys    = [exoscale_ssh_key.exemple.name]

  security_group_ids = [exoscale_security_group.bastion.id]
  elastic_ip_ids     = [exoscale_elastic_ip.bastion.id]

  labels = merge(local.labels, { role = "bastion" })

  network_interface {
    network_id = exoscale_private_network.backend.id
  }
}

# --- le tier web, sans adresse publique -----------------------------------

resource "exoscale_compute_instance" "web" {
  for_each = toset(local.web)

  zone        = var.zone
  name        = "${local.prefixe}-${each.key}"
  template_id = data.exoscale_template.ubuntu.id
  type        = var.instance_type
  disk_size   = 10
  ssh_keys    = [exoscale_ssh_key.exemple.name]

  # `private` : aucune adresse publique, même pas celle que l'API attribue par
  # défaut. C'est l'attribut qui donne au plugin d'inventaire quelque chose à
  # prouver.
  private            = true
  security_group_ids = [exoscale_security_group.web.id]

  labels = merge(local.labels, { role = "web" })

  network_interface {
    network_id = exoscale_private_network.backend.id
  }
}

# --- le tier applicatif, sur deux réseaux ---------------------------------

resource "exoscale_compute_instance" "app" {
  for_each = toset(local.app)

  zone        = var.zone
  name        = "${local.prefixe}-${each.key}"
  template_id = data.exoscale_template.ubuntu.id
  type        = var.instance_type
  disk_size   = 10
  ssh_keys    = [exoscale_ssh_key.exemple.name]

  private                 = true
  security_group_ids      = [exoscale_security_group.app.id]
  anti_affinity_group_ids = [exoscale_anti_affinity_group.app.id]

  # Le volume Block Storage, attaché ici et non par une ressource à part : le
  # fournisseur n'en a pas, et c'est l'instance qui dit ce qu'elle porte.
  block_storage_volume_ids = each.key == local.porteur_du_volume ? [exoscale_block_storage_volume.donnees.id] : []

  labels = merge(local.labels, { role = "app" })

  network_interface {
    network_id = exoscale_private_network.backend.id
  }

  network_interface {
    network_id = exoscale_private_network.monitoring.id
  }
}
