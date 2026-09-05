# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Paramètres communs à tous les modules, documentés une fois."""

from __future__ import annotations


class ModuleDocFragment:
    DOCUMENTATION = r"""
options:
  api_key:
    description:
      - Exoscale API key.
      - Falls back to the E(EXOSCALE_API_KEY) environment variable.
    type: str
    required: true
  api_secret:
    description:
      - Exoscale API secret.
      - Falls back to the E(EXOSCALE_API_SECRET) environment variable.
    type: str
    required: true
  zone:
    description:
      - Exoscale zone the request is sent to, for example V(ch-gva-2).
      - The API host carries the zone (C(api-{zone}.exoscale.com)), not the path.
      - Falls back to the E(EXOSCALE_ZONE) environment variable.
    type: str
    required: true
  api_url:
    description:
      - Full base URL of the API, C(/v2) included, overriding the one built from I(zone).
      - Meant for a local emulator or a test endpoint.
      - Falls back to the E(EXOSCALE_API_URL) environment variable, then to
        E(EXOSCALE_API_ENDPOINT), the name the C(exo) CLI and feint use.
    type: str
requirements:
  - exoscale >= 0.16 (the official Python SDK)
"""

    WAIT = r"""
options:
  wait:
    description:
      - Whether to wait for the asynchronous operation to complete.
      - Every write on the Exoscale API answers with an operation object;
        when false, the module returns as soon as the operation is accepted,
        and C(operation.state) says C(pending).
    type: bool
    default: true
  wait_timeout:
    description:
      - Maximum number of seconds to wait for the operation.
    type: int
    default: 600
"""
