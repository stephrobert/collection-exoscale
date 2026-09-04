"""Télécharge le contrat OpenAPI v2 d'Exoscale, et le versionne tel quel.

Exoscale publie un document unique pour tous ses produits, et deux adresses le
servent : `https://openapi-v2.exoscale.com/source.json`, la source de la
documentation de référence, et
`https://community.exoscale.com/reference/api/exoscale-openapi-spec.json`.
Mesuré le 4 septembre 2026 : la première porte 261 chemins, la seconde 259
(sans `/ai/api-key/{id}/reveal` ni `/ai/api-key/{id}/rotate`). C'est la
première qui est retenue, parce qu'elle est celle que le SDK Python officiel
embarque et la plus à jour des deux.

Le document est versionné octet pour octet, sans reformatage : c'est ce qui
permet à `git diff` de dire exactement ce qu'Exoscale a changé.

    python scripts/sync_specs.py            # met à jour specs/exoscale/exoscale.v2.json
"""

from __future__ import annotations

import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC_ROOT = ROOT / "specs" / "exoscale"

SOURCE_URL = "https://openapi-v2.exoscale.com/source.json"
VERSION = "v2"
TIMEOUT_SECONDS = 60


def download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "exoscale-ansible-generator"})
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        if response.status != 200:
            raise SystemExit(f"{url} : HTTP {response.status}")
        payload: bytes = response.read()
        return payload


def main() -> int:
    target = SPEC_ROOT / f"exoscale.{VERSION}.json"
    try:
        payload = download(SOURCE_URL)
    except (urllib.error.URLError, urllib.error.HTTPError) as error:
        # Un échec ne laisse jamais un fichier périmé passer pour un contrat à jour.
        print(f"échec : {SOURCE_URL} : {error}", file=sys.stderr)
        return 1
    previous = target.read_bytes() if target.is_file() else b""
    target.write_bytes(payload)
    etat = "inchangé" if payload == previous else "mis à jour"
    print(f"{target.relative_to(ROOT)} : {len(payload)} octets, {etat}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
