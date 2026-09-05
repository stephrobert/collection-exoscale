# Ce que la stack accepte, et pourquoi chaque valeur existe.

variable "endpoint" {
  description = "URL de l'émulateur, `/v2` compris, telle que `feint env exoscale` l'exporte. Vide pour viser la vraie organisation Exoscale."
  type        = string
  default     = ""

  validation {
    # Le fournisseur lit cette adresse dans l'environnement avec `/v2` dans la
    # valeur. Une adresse nue ici serait recopiée nue dans l'environnement par
    # qui relit ce fichier, et le fournisseur parlerait à un chemin qui n'existe
    # pas.
    condition     = var.endpoint == "" || endswith(var.endpoint, "/v2")
    error_message = "endpoint doit se terminer par /v2, comme `feint env exoscale` l'exporte."
  }
}

variable "zone" {
  description = "La zone Exoscale. L'émulateur n'en sert qu'une par processus, et le lanceur transmet celle que `feint env exoscale` exporte."
  type        = string
  default     = "ch-gva-2"
}

# Le marqueur qui rend chaque ressource attribuable à une exécution précise.
#
# Le contrôle de résidu compare l'organisation avant et après, et ce marqueur
# est ce qui permet de dire, devant une ressource survivante, de quelle
# exécution elle vient. Il est porté par le label `exemple` partout où l'API
# accepte un label, et par le préfixe du nom ailleurs.
variable "run_id" {
  description = "Marqueur unique de l'exécution, porté par le nom et le label `exemple`."
  type        = string
}

variable "ssh_public_key" {
  description = "Clé publique enregistrée dans l'organisation, pour que les machines démarrent avec."
  type        = string
}

variable "instance_type" {
  description = "Type des machines, `famille.taille`. standard.tiny est le moins cher qui tienne."
  type        = string
  default     = "standard.tiny"
}

variable "template" {
  description = "Le modèle public dont chaque machine démarre. Résolu par son nom, dans la zone."
  type        = string
  default     = "Linux Ubuntu 24.04 LTS 64-bit"
}

locals {
  # Un préfixe court, porté par chaque nom : les ressources que l'API ne sait
  # pas étiqueter, la clé SSH, les groupes de sécurité, restent attribuables.
  prefixe = "exo-${var.run_id}"

  # Le label que porte tout ce que l'API accepte d'étiqueter. L'inventaire
  # d'exemple filtre dessus, et le playbook filtre par préfixe ensuite.
  labels = {
    exemple = var.run_id
  }

  # Les machines, par étage. **Fixes et non variables** : le playbook d'exemple
  # compte six machines et cinq baux sur le réseau backend, et une variable qui
  # casserait ces assertions en silence serait un piège.
  web = ["web-1", "web-2"]
  app = ["worker-a", "worker-b"]

  # La machine applicative qui porte le volume Block Storage. Une seule : un
  # volume ne s'attache qu'à une machine.
  porteur_du_volume = "worker-b"
}
