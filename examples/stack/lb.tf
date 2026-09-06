# Le pool d'instances et le load balancer qui le sert.
#
# Un pool d'une machine, et non de zéro : le playbook le porte à deux puis le
# ramène à une, et lit le membre pour remettre ses labels à zéro. Le pool ne
# rejoint aucun réseau privé, et c'est délibéré : le playbook compte cinq baux
# sur le réseau backend, un par machine nommée, et l'inventaire reconnaît le
# membre du pool par son gestionnaire, pas par une adresse privée.

resource "exoscale_instance_pool" "web" {
  zone          = var.zone
  name          = "${local.prefixe}-pool"
  description   = "le pool que le load balancer sert"
  template_id   = data.exoscale_template.ubuntu.id
  instance_type = var.instance_type
  size          = 1
  disk_size     = 10
  key_pair      = exoscale_ssh_key.exemple.name

  # Les membres portent le préfixe : le playbook compte six machines par lui.
  instance_prefix    = "${local.prefixe}-pool"
  security_group_ids = [exoscale_security_group.web.id]

  labels = merge(local.labels, { role = "pool" })
}

resource "exoscale_nlb" "web" {
  zone        = var.zone
  name        = "${local.prefixe}-lb"
  description = "l'entrée publique du tier web"
  labels      = local.labels
}

resource "exoscale_nlb_service" "web" {
  zone   = var.zone
  nlb_id = exoscale_nlb.web.id
  name   = "web"

  instance_pool_id = exoscale_instance_pool.web.id
  protocol         = "tcp"
  port             = 80
  target_port      = 80
  strategy         = "round-robin"

  healthcheck {
    mode     = "tcp"
    port     = 80
    interval = 10
    timeout  = 5
    retries  = 1
  }
}
