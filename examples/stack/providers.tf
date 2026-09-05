# Le fournisseur, le plancher de version qui rend la stack sûre, et la seule
# chose qui change entre l'émulateur et le cloud.
#
# Une stack, deux cibles. `endpoint` vide vise la vraie organisation Exoscale
# et laisse le fournisseur lire les identifiants de l'environnement, comme
# n'importe quel projet ; `endpoint` renseigné vise l'émulateur et fournit la
# paire factice qu'il accepte. Écrire deux stacks pour deux cibles reviendrait
# à ne prouver ni l'une ni l'autre. La première version de ce dépôt bâtissait
# la plateforme par le SDK Python, parce que le fournisseur Terraform ne savait
# pas viser l'émulateur ; ce défaut est corrigé en amont, et la plateforme n'a
# plus qu'une seule source.
#
# **Le fournisseur n'a aucun attribut d'endpoint.** Il lit
# `EXOSCALE_API_ENDPOINT`, `/v2` compris dans la valeur, que `feint env
# exoscale` exporte et que le lanceur transmet. La variable `endpoint` ne peut
# donc pas lui être passée : elle est l'interrupteur des identifiants, et rien
# d'autre. Ce que ça garantit quand même : une stack qui déclare viser
# l'émulateur sans que l'environnement porte son adresse échoue en 403 sur la
# vraie API, avec la paire factice, au lieu d'y créer quoi que ce soit.

terraform {
  required_version = ">= 1.7.0"
  required_providers {
    exoscale = {
      source = "exoscale/exoscale"
      # Version exacte, et 0.71.0 est un plancher avant d'être une épingle.
      #
      # En dessous, le client v2 du fournisseur n'honorait pas
      # `EXOSCALE_API_ENDPOINT` : un `apply` se **scindait** entre l'émulateur
      # et un compte payant, dans la même exécution, avec les identifiants que
      # l'environnement portait (exoscale/terraform-provider-exoscale#573,
      # feint#525). feint l'a mesuré le 5 septembre 2026, par un proxy qui
      # enregistre chaque hôte demandé, et avec son témoin :
      #
      #   provider   apply       second plan          destroy       hôtes sur le fil
      #   v0.70.0    15 créées   aucun changement     15 détruites   57 vers api-ch-*
      #   v0.71.0    15 créées   aucun changement     15 détruites   AUCUN
      #
      # La ligne v0.70.0 est ce qui donne son sens à la seconde : un transcript
      # vide ne prouve rien tant que l'instrument n'a pas montré qu'il sait en
      # produire un plein. L'émulateur refuse par user agent tout fournisseur
      # plus ancien, et le lanceur vérifie la version résolue avant d'appliquer
      # quoi que ce soit : trois barrières, et aucune ne repose sur les deux
      # autres.
      #
      # Exacte et non flottante, pour la raison que scaleway a mesurée : une
      # contrainte `>= 0.71.0` résout la dernière version publiée, donc une CI
      # rouge le jour où le fournisseur change sans qu'une ligne ait bougé ici.
      # Monter de version est une décision, et elle se relit dans un diff.
      version = "0.71.0"
    }
  }
}

provider "exoscale" {
  # Contre l'émulateur, la paire que `feint env exoscale` exporte, et que feint
  # accepte sans la vérifier. Contre le cloud réel, `null` laisse le
  # fournisseur lire `EXOSCALE_API_KEY` et `EXOSCALE_API_SECRET`, puis son
  # fichier de configuration, dans cet ordre.
  key    = var.endpoint != "" ? "EXOxxxxxxxxxxxxxxxxxxxx" : null
  secret = var.endpoint != "" ? "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" : null
}
