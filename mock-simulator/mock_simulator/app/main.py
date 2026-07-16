"""Entry point for the mock-simulator container.

Reads config from environment / defaults, starts the simulation loop.
"""

from __future__ import annotations

import os
import sys
from typing import Any

from mock_simulator.app.config import SimulatorConfig
from mock_simulator.app.ingest_client import IngestClient
from mock_simulator.app.simulator import Simulator


def _get_zones_from_backend() -> list[dict[str, Any]]:
    """Stub: return hardcoded zone list matching the seed data.

    Matches backend/app/seed/data.py.
    """
    return [
        {"zone_id": "zone_east_concourse", "capacity_estimate": 8500},
        {"zone_id": "zone_west_concourse", "capacity_estimate": 8500},
        {"zone_id": "zone_north_concourse", "capacity_estimate": 6000},
        {"zone_id": "zone_south_concourse", "capacity_estimate": 6000},
        {"zone_id": "zone_gate_1", "capacity_estimate": 3000},
        {"zone_id": "zone_gate_4", "capacity_estimate": 2000},
        {"zone_id": "zone_gate_7", "capacity_estimate": 2000},
        {"zone_id": "zone_gate_10", "capacity_estimate": 1500},
        {"zone_id": "zone_med_east", "capacity_estimate": 50},
        {"zone_id": "zone_med_west", "capacity_estimate": 50},
        {"zone_id": "zone_gs_east", "capacity_estimate": 100},
        {"zone_id": "zone_gs_west", "capacity_estimate": 100},
        {"zone_id": "zone_seating_100", "capacity_estimate": 12000},
        {"zone_id": "zone_seating_200", "capacity_estimate": 8000},
    ]


def _get_volunteers_from_backend() -> list[dict[str, Any]]:
    """Stub: return hardcoded volunteer list matching the seed data."""
    return [
        {"volunteer_id": "vol_maria_alvarez", "assigned_zone_id": "zone_east_concourse"},
        {"volunteer_id": "vol_john_chen", "assigned_zone_id": "zone_west_concourse"},
        {"volunteer_id": "vol_amina_walker", "assigned_zone_id": "zone_north_concourse"},
        {"volunteer_id": "vol_carlos_rodriguez", "assigned_zone_id": "zone_south_concourse"},
        {"volunteer_id": "vol_devon_price", "assigned_zone_id": "zone_east_concourse"},
    ]


def main() -> None:
    config = SimulatorConfig()

    if os.environ.get("SIMULATOR_BACKEND_URL"):
        config.backend_url = os.environ["SIMULATOR_BACKEND_URL"]
    if os.environ.get("SIMULATOR_SEED"):
        config.random_seed = int(os.environ["SIMULATOR_SEED"])
    if os.environ.get("SIMULATOR_INTERVAL"):
        config.incident_mean_interval_seconds = float(os.environ["SIMULATOR_INTERVAL"])
    if os.environ.get("SIMULATOR_AUTH_TOKEN"):
        config.internal_auth_token = os.environ["SIMULATOR_AUTH_TOKEN"]

    zones = _get_zones_from_backend()
    volunteers = _get_volunteers_from_backend()
    client = IngestClient(config.backend_url, config.internal_auth_token)

    sim = Simulator(config, zones, volunteers, client)
    print(f"[simulator] Starting — seed={config.random_seed}, "
          f"backend={config.backend_url}, "
          f"mean_interval={config.incident_mean_interval_seconds}s")

    try:
        sim.run(live=True)
    except KeyboardInterrupt:
        print("\n[simulator] Shutting down")
        sys.exit(0)


if __name__ == "__main__":
    main()
