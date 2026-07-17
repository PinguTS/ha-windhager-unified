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
# Configured node names from discovery (display-only, never part of identifiers).
CONF_NODE_NAMES = "node_names"
# OIDs the user explicitly deselected during a re-scan; never offered again as new.
CONF_EXCLUDED_OIDS = "excluded_oids"
# Transient checkbox in the options flow that triggers a full re-scan.
CONF_RESCAN = "rescan_network"

# History storage profile options
CONF_HISTORY_STORAGE_MODE = "history_storage_mode"
CONF_HISTORY_SAMPLE_INTERVAL = "history_sample_interval"
CONF_HISTORY_RETENTION_DAYS = "history_retention_days"

HISTORY_MODE_HOME_ASSISTANT = "home_assistant"
HISTORY_MODE_CRITICAL = "critical"
HISTORY_MODE_ALL_MARKED = "all_marked"

HISTORY_STORAGE_MODES: tuple[str, ...] = (
    HISTORY_MODE_HOME_ASSISTANT,
    HISTORY_MODE_CRITICAL,
    HISTORY_MODE_ALL_MARKED,
)

DEFAULT_HISTORY_STORAGE_MODE = HISTORY_MODE_HOME_ASSISTANT
DEFAULT_HISTORY_SAMPLE_INTERVAL = 300  # seconds
DEFAULT_HISTORY_RETENTION_DAYS = 730

MIN_HISTORY_SAMPLE_INTERVAL = 30
MAX_HISTORY_SAMPLE_INTERVAL = 3600
MIN_HISTORY_RETENTION_DAYS = 30
MAX_HISTORY_RETENTION_DAYS = 3650

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

# LON datapoint entity roles (explicit in oids.yaml or derived).
ROLE_MEASUREMENT = "measurement"
ROLE_DIAGNOSTIC = "diagnostic"
ROLE_CONFIG = "config"
ROLE_COMMAND = "command"

DEFAULT_COMMAND_VALUE = "1"

CONFIG_ENTRY_VERSION = 2

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.NUMBER,
    Platform.SWITCH,
    Platform.BUTTON,
    Platform.SELECT,
]
