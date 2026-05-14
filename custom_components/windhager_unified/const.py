from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "windhager_unified"
DEFAULT_NAME = "Windhager"
DEFAULT_SCAN_INTERVAL = 30  # seconds

# Configuration keys
CONF_HOST = "host"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_VERIFY_SSL = "verify_ssl"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_EXPERIENCE_LEVEL = "experience_level"
CONF_GROUPS = "groups"
CONF_REFRESH_LABELS = "refresh_labels_from_device"
# Serialized from last config-flow discovery (tier-scoped lookup walk).
CONF_DISCOVERED_DATAPOINTS = "discovered_datapoints"
# Ad-hoc OID entries added via ``windhager_unified.add_datapoint`` service
# (list of ``{"oid": "...", "group": "boiler"}`` or legacy list of OID strings).
CONF_ADHOC_OIDS = "adhoc_oids"

# Experience tier slugs — ordered from least to most detail.
# The ordering is used for ordinal comparisons:
#   experience_minimum <= selected_tier  →  include the datapoint.
EXPERIENCE_TIERS: tuple[str, ...] = (
    "essential",
    "comfort",
    "advanced",
    "expert",
    "service",
)

DEFAULT_EXPERIENCE_LEVEL = "essential"

# Default experience_minimum when a datapoint/endpoint does not declare one.
# LON datapoints default to "expert"; REST actuators default to "service".
DEFAULT_LON_EXPERIENCE_MINIMUM = "expert"
DEFAULT_REST_SENSOR_EXPERIENCE_MINIMUM = "advanced"
DEFAULT_REST_ACTUATOR_EXPERIENCE_MINIMUM = "service"

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.BUTTON,
    Platform.SELECT,
]
