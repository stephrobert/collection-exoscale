# Ce que la stack rend, et ce qui en fait la valeur pour l'exemple Ansible.
#
# L'inventaire dynamique découvre les machines tout seul : ces sorties ne
# servent donc pas à les lister, ce serait doubler ce qu'on veut prouver. Elles
# donnent ce que l'inventaire ne peut pas connaître, par où entrer et par où
# vérifier, et ce que le contrôle du plan de contrôle lit auprès de l'API sans
# passer par la collection.

output "run_id" {
  description = "Le marqueur porté par chaque ressource, pour le contrôle de résidu."
  value       = var.run_id
}

output "prefixe" {
  description = "Le préfixe des noms. Le playbook filtre par lui."
  value       = local.prefixe
}

output "zone" {
  description = "La zone où la plateforme a été bâtie."
  value       = var.zone
}

output "bastion_ip" {
  description = "La seule adresse publique de la plateforme. Point d'entrée SSH."
  value       = exoscale_elastic_ip.bastion.ip_address
}

output "application_url" {
  description = "L'adresse par laquelle une requête traverse le load balancer."
  value       = "http://${exoscale_nlb.web.ip_address}"
}

output "attendu" {
  description = "Ce que l'exemple doit trouver. Un compte, pas une liste : c'est l'inventaire qui liste."
  value = {
    bastion = 1
    web     = length(local.web)
    app     = length(local.app)
    pool    = exoscale_instance_pool.web.size
    total   = 1 + length(local.web) + length(local.app) + exoscale_instance_pool.web.size
  }
}

output "ids" {
  description = "Les identifiants que le contrôle du plan de contrôle relit auprès de l'API."
  value = {
    ssh_key                = exoscale_ssh_key.exemple.name
    anti_affinity_group    = exoscale_anti_affinity_group.app.id
    elastic_ip             = exoscale_elastic_ip.bastion.id
    instance_pool          = exoscale_instance_pool.web.id
    load_balancer          = exoscale_nlb.web.id
    load_balancer_service  = exoscale_nlb_service.web.id
    block_storage_volume   = exoscale_block_storage_volume.donnees.id
    block_storage_snapshot = exoscale_block_storage_volume_snapshot.donnees.id
    security_groups = {
      bastion = exoscale_security_group.bastion.id
      web     = exoscale_security_group.web.id
      app     = exoscale_security_group.app.id
    }
    private_networks = {
      backend    = exoscale_private_network.backend.id
      monitoring = exoscale_private_network.monitoring.id
    }
    instances = merge(
      { bastion = exoscale_compute_instance.bastion.id },
      { for nom, machine in exoscale_compute_instance.web : nom => machine.id },
      { for nom, machine in exoscale_compute_instance.app : nom => machine.id },
    )
  }
}
