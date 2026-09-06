# Le réseau : deux réseaux privés gérés, et un groupe de sécurité par étage.
#
# **Gérés, avec une plage** : c'est l'API qui distribue les baux, et c'est dans
# les baux du réseau, pas sur l'instance, que le plugin d'inventaire lit
# l'adresse privée de chaque machine. Un réseau sans plage ne donnerait aucun
# bail, et l'inventaire ne verrait que le bastion.

resource "exoscale_private_network" "backend" {
  zone        = var.zone
  name        = "${local.prefixe}-backend"
  description = "le réseau que toutes les machines de la plateforme partagent"
  labels      = local.labels

  start_ip = "10.42.0.10"
  end_ip   = "10.42.0.250"
  netmask  = "255.255.255.0"
}

# Le second réseau ne porte que le tier applicatif : c'est ce qui prouve que
# l'inventaire sait choisir une adresse **par réseau**, et pas la première
# venue. Une machine sur un seul réseau ne prouverait rien de cette sélection.
resource "exoscale_private_network" "monitoring" {
  zone        = var.zone
  name        = "${local.prefixe}-monitoring"
  description = "le réseau que seul le tier applicatif rejoint"
  labels      = local.labels

  start_ip = "10.43.0.10"
  end_ip   = "10.43.0.250"
  netmask  = "255.255.255.0"
}

# --- ce que chaque étage accepte ------------------------------------------
#
# Un groupe de sécurité Exoscale ne filtre que l'interface publique. Sur les
# tiers qui n'ont aucune adresse publique, ces règles ne rencontrent aucun
# paquet ; elles disent quand même ce que l'étage accepte le jour où il en a
# une, et sur les membres du pool, qui portent une adresse publique, elles
# filtrent pour de bon. Un groupe de sécurité ne porte pas de label : c'est
# son nom qui l'attribue à l'exécution.

resource "exoscale_security_group" "bastion" {
  name        = "${local.prefixe}-bastion"
  description = "SSH depuis Internet, et rien d'autre"
}

resource "exoscale_security_group_rule" "bastion_ssh" {
  security_group_id = exoscale_security_group.bastion.id
  type              = "INGRESS"
  protocol          = "TCP"
  cidr              = "0.0.0.0/0"
  start_port        = 22
  end_port          = 22
}

resource "exoscale_security_group" "web" {
  name        = "${local.prefixe}-web"
  description = "HTTP depuis le load balancer, SSH depuis le bastion"
}

resource "exoscale_security_group_rule" "web_http" {
  security_group_id = exoscale_security_group.web.id
  type              = "INGRESS"
  protocol          = "TCP"
  cidr              = "0.0.0.0/0"
  start_port        = 80
  end_port          = 80
}

# Nommée par groupe et non par adresse : c'est la règle qu'une plateforme
# écrit vraiment, et le bastion peut changer d'adresse sans qu'elle bouge.
resource "exoscale_security_group_rule" "web_ssh" {
  security_group_id      = exoscale_security_group.web.id
  type                   = "INGRESS"
  protocol               = "TCP"
  user_security_group_id = exoscale_security_group.bastion.id
  start_port             = 22
  end_port               = 22
}

resource "exoscale_security_group" "app" {
  name        = "${local.prefixe}-app"
  description = "le port applicatif depuis le tier web, SSH depuis le bastion"
}

resource "exoscale_security_group_rule" "app_port" {
  security_group_id      = exoscale_security_group.app.id
  type                   = "INGRESS"
  protocol               = "TCP"
  user_security_group_id = exoscale_security_group.web.id
  start_port             = 8080
  end_port               = 8080
}

resource "exoscale_security_group_rule" "app_ssh" {
  security_group_id      = exoscale_security_group.app.id
  type                   = "INGRESS"
  protocol               = "TCP"
  user_security_group_id = exoscale_security_group.bastion.id
  start_port             = 22
  end_port               = 22
}
