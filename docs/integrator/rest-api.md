# Windhager REST API Reference

Generated from Swagger 1.2 source files in `docs/swagger/`.
Do not edit by hand — run `python scripts/build_docs.py` to regenerate.

## DcmRC7030 v1.0

### `GET /DcmRC7030/api/1.0/info/{id}`

**Retrieve id info**

Retrieve id info

*Nickname:* `getInfoId`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `id` | path | string | yes | Info id to be retrieve |

### Models

#### `InfoModel`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `name` | string |  |
| `version` | string |  |

### `PUT /DcmRC7030/api/1.0/msg1025/push`

**push msg1025**

push msg1025

*Nickname:* `putPush`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `body` | body | Srv1025Model | yes | Srv1025Model object to action on. |

### Models

#### `Srv1025Model`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `data` | ? |  |
| `fctId` | integer |  |
| `groupId` | integer |  |
| `memberId` | integer |  |
| `nodeId` | integer |  |
| `propChanged` | integer |  |
| `subnet` | integer |  |
| `typeId` | integer |  |

### `GET /DcmRC7030/api/1.0/settings`

**get settings list**

Returns a list of all key-value pairs.

*Nickname:* `getList`  
*Returns:* void

### `GET /DcmRC7030/api/1.0/settings/allKeys`

**get list af all keys**

Returns a list of all keys, including subkeys, that can be read using this service.

*Nickname:* `getAllKeys`  
*Returns:* void

### `GET /DcmRC7030/api/1.0/settings/{key}`

**get settings value from key**

get settings value from key

*Nickname:* `getKeyValue`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `key` | path | string | yes | settings key. |

### `PUT /DcmRC7030/api/1.0/settings/{key}`

**update value value for key**

update value value for key

*Nickname:* `putKeyValue`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `key` | path | string | yes | settings key. |
| `value` | query | string | yes | value for key. |

### `PUT /DcmRC7030/api/1.0/settings/logging/level`

**update logging level**

update logging level

*Nickname:* `putLoggingLevel`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `value` | query | string | yes | level id to be updated. |

### `POST /DcmRC7030/api/1.0/settings/reset/all`

**reset all settings**

reset all settings

*Nickname:* `postResetAll`  
*Returns:* void

### Models

#### `INFO`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `name` | string |  |
| `version` | string |  |

#### `SettingsModel`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `key` | string |  |
| `value` | string |  |

## InfoWinFehlerlog v1.0

### `GET /InfoWinFehlerlog/api/1.0/fehlerlog`

**Retrieve fehlerlog list**

Retrieve fehlerlog list

*Nickname:* `getFehlerlog`  
*Returns:* void

### `POST /InfoWinFehlerlog/api/1.0/fehlerlog`

**Add new fehlerlog item**

Add new fehlerlog item

*Nickname:* `postFehlerlog`  
*Returns:* Status

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `fehlerlog` | body | FehlerlogModel | yes | The `fehlerlog` Object to perform action with. |

### `GET /InfoWinFehlerlog/api/1.0/fehlerlog/rawlist`

**Retrieve fehlerlog raw list**

Retrieve fehlerlog raw list

*Nickname:* `getFehlerlog`  
*Returns:* void

### `GET /InfoWinFehlerlog/api/1.0/fehlerlog/{id}`

**Retrieve fehlerlog at 'id'**

Retrieve fehlerlog ad 'id'

*Nickname:* `getFehlerlogId`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `id` | path | integer | yes | id to perform action with. |

### `PUT /InfoWinFehlerlog/api/1.0/fehlerlog/{id}`

**Update fehlerlog.status at 'id'**

Update fehlerlog.status ad 'id'

*Nickname:* `putFehlerlogId`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `id` | path | integer | yes | id to perform action with. |
| `status` | query | string | yes | 'status' to perform action with. |

### `DELETE /InfoWinFehlerlog/api/1.0/fehlerlog/{id}`

**Delete fehlerlog at 'id'**

Delete fehlerlog ad 'id'

*Nickname:* `deleteFehlerlogId`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `id` | path | integer | yes | id to perform action with. |

### `PUT /InfoWinFehlerlog/api/1.0/fehlerlog/reset/{id}`

**Reset id (Quittierung)**

Reset id (Quittierung)

*Nickname:* `putFehlerlogResetId`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `id` | path | integer | yes | id to perform action with. |

### `POST /InfoWinFehlerlog/api/1.0/fehlerlog/{subnetId}/{nodeId}`

**Add 'eBUS FE01' message**

Add 'eBUS FE01' message

*Nickname:* `postFehlerlogSubnetId`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `subnetId` | path | integer | yes | Numeric `id` of the subnet to perform action with. (for RC7030 it is always 1). |
| `nodeId` | path | integer | yes | Numeric `id` of the `Node` to perform action with. |
| `value` | query | string | yes | 'eBUS FE01 Message' or 'error code' to perform action with. |

### Models

#### `FehlerlogModel`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `code` | integer |  |
| `id` | integer |  |
| `timestamp` | string |  |

#### `Status`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `code` | integer |  |
| `message` | string |  |

### `GET /InfoWinFehlerlog/api/1.0/info/{id}`

**Retrieve id info**

Retrieve id info

*Nickname:* `getInfoId`  
*Returns:* InfoModel

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `id` | path | string | yes | Info id to be retrieve |

### Models

#### `InfoModel`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `name` | string |  |
| `version` | string |  |

### `GET /InfoWinFehlerlog/api/1.0/settings`

**get settings list**

Returns a list of all key-value pairs.

*Nickname:* `getList`  
*Returns:* void

### `GET /InfoWinFehlerlog/api/1.0/settings/allKeys`

**get list af all keys**

Returns a list of all keys, including subkeys, that can be read using this service.

*Nickname:* `getAllKeys`  
*Returns:* void

### `GET /InfoWinFehlerlog/api/1.0/settings/{key}`

**get settings value from key**

get settings value from key

*Nickname:* `getKeyValue`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `key` | path | string | yes | settings key. |

### `PUT /InfoWinFehlerlog/api/1.0/settings/{key}`

**update value value for key**

update value value for key

*Nickname:* `putKeyValue`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `key` | path | string | yes | settings key. |
| `value` | query | string | yes | value for key. |

### `PUT /InfoWinFehlerlog/api/1.0/settings/logging/level`

**update logging level**

update logging level

*Nickname:* `putLoggingLevel`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `value` | query | string | yes | level id to be updated. |

### Models

#### `INFO`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `name` | string |  |
| `version` | string |  |

#### `SettingsModel`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `key` | string |  |
| `value` | string |  |

## InfoWinHeartbeat v1.0 *(used by integration)*

### `GET /InfoWinHeartbeat/api/1.0/heartbeat`

**Retrieve current heartbeat**

Retrieve current heartbeat

*Nickname:* `getHeartbeat`  
*Returns:* void

### `POST /InfoWinHeartbeat/api/1.0/heartbeat`

**Create new heartbeat**

Create new heartbeat

*Nickname:* `postHeartbeat`  
*Returns:* Status

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `heartbeat` | body | POST_HeartbeatModel | yes | The `heartbeat` Object to perform action with. |

### `DELETE /InfoWinHeartbeat/api/1.0/heartbeat`

**Delete (stop) current heartbeat**

Delete (stop) current heartbeat

*Nickname:* `deleteHeartbeat`  
*Returns:* void

### `PUT /InfoWinHeartbeat/api/1.0/heartbeat/{subnet}/{nodeId}`

**update heartbeat (Indication from subnet/nodeId)**

update heartbeat (Indication from subnet/nodeId)

*Nickname:* `putHeartbeatSubnetNodeId`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `subnet` | path | integer | yes | Numeric `id` of the subnet to perform action with. (for RC7030 it is always 1). |
| `nodeId` | path | integer | yes | Numeric `id` of the `Node` to perform action with. |
| `value` | query | string | yes | value decimal or hex with prepanding 0x |

### Models

#### `POST_HeartbeatModel`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `interval` | integer |  |
| `nodeId` | integer |  |
| `subnet` | integer |  |

#### `Status`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `code` | integer |  |
| `message` | string |  |

### `GET /InfoWinHeartbeat/api/1.0/info/{id}`

**Retrieve id info**

Retrieve id info

*Nickname:* `getInfoId`  
*Returns:* InfoModel

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `id` | path | string | yes | Info id to be retrieve |

### Models

#### `InfoModel`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `name` | string |  |
| `version` | string |  |

### `GET /InfoWinHeartbeat/api/1.0/kesselwahl/{method}`

**Retrieve kesselwahl**

Retrieve kesselwahl

*Nickname:* `getHeartbeat`  
*Returns:* KesselwahlModel

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `method` | path | string | yes | method to perform action with. |

### `PUT /InfoWinHeartbeat/api/1.0/kesselwahl/{id}`

**start kesselwahl**

start kesselwahl

*Nickname:* `putKesselwahl`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `id` | path | string | yes | id des Kesssels. |
| `option` | query | string | no | Option. |

### `PUT /InfoWinHeartbeat/api/1.0/kesselwahl/servicepin`

**new servicepin message**

new servicepin message

*Nickname:* `putServicepin`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `londevice` | body | LonDeviceModel | yes | The `LonDevice` Object to perform action with. |

### `GET /InfoWinHeartbeat/api/1.0/kesselwahl/servicepin/listener`

**get servicepin listener state**

get servicepin listener state

*Nickname:* `getServicepinListener`  
*Returns:* void

### `POST /InfoWinHeartbeat/api/1.0/kesselwahl/servicepin/listener/{method}`

**post service listener method**

post service listener method

*Nickname:* `postServicepinListenerEvent`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `method` | path | string | yes | post servicepin listener method. |

### Models

#### `KesselwahlModel`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `id` | integer |  |
| `name` | integer |  |

#### `LonDeviceModel`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `domainIdx` | integer |  |
| `neuronId` | string |  |
| `nodeId` | integer |  |
| `programId` | string |  |
| `subnet` | integer |  |

### `GET /InfoWinHeartbeat/api/1.0/settings`

**get settings list**

Returns a list of all key-value pairs.

*Nickname:* `getList`  
*Returns:* void

### `GET /InfoWinHeartbeat/api/1.0/settings/allKeys`

**get list af all keys**

Returns a list of all keys, including subkeys, that can be read using this service.

*Nickname:* `getAllKeys`  
*Returns:* void

### `GET /InfoWinHeartbeat/api/1.0/settings/{key}`

**get settings value from key**

get settings value from key

*Nickname:* `getKeyValue`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `key` | path | string | yes | settings key. |

### `PUT /InfoWinHeartbeat/api/1.0/settings/{key}`

**update value value for key**

update value value for key

*Nickname:* `putKeyValue`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `key` | path | string | yes | settings key. |
| `value` | query | string | yes | value for key. |

### `PUT /InfoWinHeartbeat/api/1.0/settings/logging/level`

**update logging level**

update logging level

*Nickname:* `putLoggingLevel`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `value` | query | string | yes | level id to be updated. |

### Models

#### `INFO`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `name` | string |  |
| `version` | string |  |

#### `SettingsModel`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `key` | string |  |
| `value` | string |  |

## RestApiRC7030 v1.0 *(used by integration)*

### `GET /api/1.0/config/network`

**Network configuration**

Retrieve NetworkConfig Object.

*Nickname:* `getNetworkConfig`  
*Returns:* NetworkConfig

### `PUT /api/1.0/config/network`

**Update Network configuration**

Update NetworkConfig Object.

*Nickname:* `putNetworkConfig`  
*Returns:* Status

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `networkConfig` | body | NetworkConfig | yes | NetworkConfig JSON |

### `GET /api/1.0/config/DynIP`

**DynIp configuration**

Retrieve DynIpConfig Object.

*Nickname:* `getDynIpConfig`  
*Returns:* DynIpConfig

### `PUT /api/1.0/config/DynIP`

**Update DynIP configuration**

Update DynIpConfig Object.

*Nickname:* `putDynIpConfig`  
*Returns:* Status

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `dynIpConfig` | body | DynIpConfig | yes | DynIpConfig JSON |

### `GET /api/1.0/config/Alarm`

**Alarm configuration**

Retrieve AlarmConfig Object.

*Nickname:* `getAlarmConfig`  
*Returns:* AlarmConfig

### `PUT /api/1.0/config/Alarm`

**Update Alarm configuration**

Update AlarmConfig configuration.

*Nickname:* `putAlarmConfig`  
*Returns:* Status

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `alarmConfig` | body | AlarmConfig | yes | AlarmConfig JSON |

### Models

#### `AlarmConfig`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `active` | boolean | enable Alarm service |
| `baseURL` | string | The base URL for the API |
| `prop` | string |  |

#### `DynIpConfig`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `active` | boolean | enable DynIP service |
| `baseURL` | string | The base URL for the API |
| `password` | string |  |
| `prop` | string |  |
| `user` | string |  |
| `vpn` | boolean | enable VPN service |

#### `Error`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `code` | integer |  |
| `fileds` | string |  |
| `message` | string |  |

#### `NetworkConfig`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `DHCP` | boolean | Use DHCP |
| `DNS` | string |  |
| `Gateway` | string |  |
| `IP` | string |  |
| `MAC` | string |  |
| `SubnetMask` | string |  |
| `WebPort` | integer |  |

#### `Status`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `code` | integer |  |
| `message` | string |  |

### `PUT /api/1.0/datapoint`

**Update Datapoint**

Update Datapoint.

*Nickname:* `putDatapoint`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `datapoint` | body | Datapoint | yes | The `OID` of the Object to perform action with. |

### `GET /api/1.0/datapoint/{subnetId}/{nodeId}/{fctId}/{groupId}/{memberId}/{varInst}`

**Retrieve Datapoint**

A single Datapoint object with all its details (identifikationsgesz. DP)

*Nickname:* `getDatpoint`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `subnetId` | path | integer | yes | Numeric `id` of the subnet to perform action with. (for RC7030 it is always 1). |
| `nodeId` | path | integer | yes | Numeric `id` of the `Node` to perform action with. |
| `fctId` | path | integer | yes | Numeric `id` of the `Function` to perform action with. |
| `groupId` | path | integer | yes | Numeric `id` of the `Group` to perform action with. |
| `memberId` | path | integer | yes | Numeric `id` of the `memberId` to perform action with. |
| `varInst` | path | integer | no | Numeric `id` of the `varInst` to perform action with. (default 0) |
| `cacheCtl` | query | integer | no | cache control 0: no cache do bypass the cache, 1: with cache (default) |

### `PUT /api/1.0/datapoint/{subnetId}/{nodeId}/{fctId}/{groupId}/{memberId}/{varInst}`

**Update Datapoint**

Update Datapoint.

*Nickname:* `putDatapointPath`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `subnetId` | path | integer | yes | Numeric `id` of the subnet to perform action with. (for RC7030 it is always 1). |
| `nodeId` | path | integer | yes | Numeric `id` of the `Node` to perform action with. |
| `fctId` | path | integer | yes | Numeric `id` of the `Function` to perform action with. |
| `groupId` | path | integer | yes | Numeric `id` of the `Group` to perform action with. |
| `memberId` | path | integer | yes | Numeric `id` of the `memberId` to perform action with. |
| `varInst` | path | integer | no | Numeric `id` of the `varInst` to perform action with. (default 0) |
| `value` | query | string | yes | new value to be set. |

### `GET /api/1.0/datapoint/{subnetId}/{nodeId}/{fctNV}/0/{nvIndex}/0`

**Retrieve NV Datapoint**

Retrieve NV Datapoint at nvIndex

*Nickname:* `getDatpointAtNvIndex`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `subnetId` | path | integer | yes | Numeric `id` of the subnet to perform action with. |
| `nodeId` | path | integer | yes | Numeric `id` of the `Node` to perform action with. |
| `fctNV` | path | integer | yes | Numeric `id` of the `NV-Function` to perform action with. |
| `nvIndex` | path | integer | yes | Numeric `nvIndex` to perform action with. |

### Models

#### `Datapoint`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `OID` | string | OID of the datapoint |
| `name` | string |  |
| `step` | string |  |
| `timestamp` | string |  |
| `typeId` | integer |  |
| `unit` | string |  |
| `unitId` | integer |  |
| `value` | string |  |
| `writeProt` | boolean |  |

#### `Error`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `code` | integer |  |
| `fileds` | string |  |
| `message` | string |  |

#### `Status`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `code` | integer |  |
| `message` | string |  |

### `GET /api/1.0/datapoints`

**Retrieve a OID Datapoint**

Retrieve one OID or a list of OID's

*Nickname:* `getDatapoint`  
*Returns:* Datapoint

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `OID` | query | string | no | The `OID` of the datapoint to perform action with. If `OID' is empty a list of all current datapoints in the `data cache` will be return.<br/>For a list of OID's use comma separated values format (csv). |

### `PUT /api/1.0/datapoints`

**Update Network configuration**

Update NetworkConfig Object.

*Nickname:* `putNetworkConfig`  
*Returns:* Status

### Models

#### `Datapoint`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `OID` | string | OID of the datapoint |
| `timestamp` | string |  |
| `unit` | string |  |
| `value` | string |  |

#### `Error`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `code` | integer |  |
| `fileds` | string |  |
| `message` | string |  |

#### `Status`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `code` | integer |  |
| `message` | string |  |

### `GET /api/1.0/DynIP/CheckIP`

**CheckIP**

Retrieves the public IP Address over the <b>DynIP Server</b> specified in <i>/config/DynIP</i> parameter: <b>baseURL</b>.

*Nickname:* `getCheckIP`  
*Returns:* void

### `PUT /api/1.0/DynIP/UpdateIP`

**UpdateIP**

Updates the public IP Address over the <b>DynIP Server</b> specified in <i>/config/DynIP</i> parameter: <b>baseURL</b>.

*Nickname:* `putUpdateIP`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `updateIpModel` | body | UpdateIpModel | yes | UpdateIpModel as JSON |

### `POST /api/1.0/DynIP/OnAlarm`

**OnAlarm**

Posts a new <i>Alarm, Error or Info Message<i> to the <b>DynIP Server</b> specified in <i>/config/OnAlarm</i> parameter: <b>baseURL</b>.

*Nickname:* `postDynIpOnAlarm`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `onAlarmModel` | body | OnAlarmModel | yes | OnAlarmModel as JSON |

### Models

#### `CheckIpModel`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `IP` | string |  |
| `status` | string |  |

#### `ErrorModel`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `code` | integer |  |
| `message` | string |  |
| `reason` | string |  |

#### `OnAlarmModel`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `MAC` | string | MAC Address formated as 'hh-hh-hh-hh-hh-hh' |
| `id` | string | id of the message |
| `msg` | string | Error/Alarm/Info message |

#### `StatusModel`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `code` | integer |  |
| `message` | string |  |

#### `UpdateIpModel`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `IP` | string | Public IP address in dot-decimal notation |
| `MAC` | string | MAC Address formated as 'hh-hh-hh-hh-hh-hh' |

### `GET /api/1.0/info/{id}`

**Retrieve id info**

Retrieve id info

*Nickname:* `getInfoId`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `id` | path | string | yes | Info id to be retrieve |

### Models

#### `InfoModel`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `name` | string |  |
| `version` | string |  |

### `GET /api/1.0/lookup`

**Subnet Collection**

List all <b>subnets</b> in the plant.

*Nickname:* `getLookup`  
*Returns:* void

### `GET /api/1.0/lookup/{subnetId}`

**Node Collection**

List all <b>nodes</b> in the <b>subnet</b>.

*Nickname:* `getLookupNodes`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `subnetId` | path | integer | yes | Numeric `id` of the subnet to perform action with. (for RC7030 it is always 1). |

### `GET /api/1.0/lookup/{subnetId}/{nodeId}`

**Retrieve a Node**

A single <b>Node</b> object with all its details.

*Nickname:* `getLookupNode`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `subnetId` | path | integer | yes | Numeric `id` of the subnet to perform action with. (for RC7030 it is always 1). |
| `nodeId` | path | integer | yes | Numeric `id` of the `Node` to perform action with. |

### `GET /api/1.0/lookup/{subnetId}/{nodeId}/{fctId}`

**Level Collection**

List all <b>levels</b> in a node function.

*Nickname:* `getLevels`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `subnetId` | path | integer | yes | Numeric `id` of the subnet to perform action with. (for RC7030 it is always 1). |
| `nodeId` | path | integer | yes | Numeric `id` of the `Node` to perform action with. |
| `fctId` | path | integer | yes | Numeric `id` of the `Function` to perform action with. |

### `GET /api/1.0/lookup/{subnetId}/{nodeId}/{fctId}/{levelId}`

**Datapoint Collection**

List all <b>Datapoints</b> in the level.

*Nickname:* `getPosDatapoints`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `subnetId` | path | integer | yes | Numeric `id` of the subnet to perform action with. (for RC7030 it is always 1). |
| `nodeId` | path | integer | yes | Numeric `id` of the `Node` to perform action with. |
| `fctId` | path | integer | yes | Numeric `id` of the `Function` to perform action with. |
| `levelId` | path | integer | yes | Numeric `id` of the `Level` to perform action with. |

### `GET /api/1.0/lookup/{subnetId}/{nodeId}/{fctId}/{levelId}/{position}`

**Retrieve Datapoint**

A single <b>Datapoint</b> object with all its details (positionsgest. DP).

*Nickname:* `getPosDatpoint`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `subnetId` | path | integer | yes | Numeric `id` of the subnet to perform action with. (for RC7030 it is always 1). |
| `nodeId` | path | integer | yes | Numeric `id` of the `Node` to perform action with. |
| `fctId` | path | integer | yes | Numeric `id` of the `Function` to perform action with. |
| `levelId` | path | integer | yes | Numeric `id` of the `Level` to perform action with. |
| `position` | path | integer | yes | Numeric `id` of the `position` to perform action with. |

### `PUT /api/1.0/lookup/{subnetId}/{nodeId}/{fctId}/{levelId}/{position}`

**Update Datapoint**

Update Datapoint (positionsgest. DP.

*Nickname:* `putPosDatapoint`  
*Returns:* Status

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `subnetId` | path | integer | yes | Numeric `id` of the subnet to perform action with. (for RC7030 it is always 1). |
| `nodeId` | path | integer | yes | Numeric `id` of the `Node` to perform action with. |
| `fctId` | path | integer | yes | Numeric `id` of the `Function` to perform action with. |
| `levelId` | path | integer | yes | Numeric `id` of the `Level` to perform action with. |
| `position` | path | integer | yes | Numeric `id` of the `position` to perform action with. |
| `value` | query | string | yes | new value to be set. |

### `GET /api/1.0/lookup/{subnetId}/{nodeId}/{fctNV}`

**NV Collection count**

NV count in a node.

*Nickname:* `getLevels`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `subnetId` | path | integer | yes | Numeric `id` of the subnet to perform action with. (for RC7030 it is always 1). |
| `nodeId` | path | integer | yes | Numeric `id` of the `Node` to perform action with. |
| `fctNV` | path | integer | yes | Numeric `id` of the `NV-Function` to perform action with. |

### `GET /api/1.0/lookup/{subnetId}/{nodeId}/{fctNV}/0`

**NV Collection**

List all <b>NV's</b> in a node.

*Nickname:* `getLevels`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `subnetId` | path | integer | yes | Numeric `id` of the subnet to perform action with. (for RC7030 it is always 1). |
| `nodeId` | path | integer | yes | Numeric `id` of the `Node` to perform action with. |
| `fctNV` | path | integer | yes | Numeric `id` of the `NV-Function` to perform action with. |

### `GET /api/1.0/lookup/{subnetId}/{nodeId}/{fctNV}/0/{nvIndex}`

**Retrieve NV Datapoint**

Retrieve NV Datapoint at nvIndex

*Nickname:* `getPosDatpoint`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `subnetId` | path | integer | yes | Numeric `id` of the subnet to perform action with. (for RC7030 it is always 1). |
| `nodeId` | path | integer | yes | Numeric `id` of the `Node` to perform action with. |
| `fctNV` | path | integer | yes | Numeric `id` of the `NV-Function` to perform action with. |
| `nvIndex` | path | integer | yes | Numeric `nvIndex` to perform action with. |

### `GET /api/1.0/lookup/units/{cat}`

**Unit Collection**

List all <b>units</b> in the database.

*Nickname:* `getLookupUnits`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `cat` | path | string | yes | category |

### Models

#### `Datapoint`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `OID` | string | OID of the datapoint |
| `timestamp` | string |  |
| `unit` | string |  |
| `value` | string |  |

#### `Error`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `code` | integer |  |
| `fileds` | string |  |
| `message` | string |  |

#### `Function`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `fctId` | integer | id of the function |
| `fctType` | integer |  |
| `lock` | bool |  |
| `name` | string |  |

#### `Level`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `count` | integer | number of the datapoints inside this level |
| `id` | integer | id of the level |

#### `Node`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `functions` | array[`Function`] |  |
| `name` | string |  |
| `neuronId` | string |  |
| `nodeId` | integer | id of the node |
| `programId` | string |  |
| `subnet` | integer |  |

#### `Status`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `code` | integer |  |
| `message` | string |  |

#### `Subnet`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `id` | integer | id of the subnet |
| `name` | string | name of the subnet |

### `GET /api/1.0/nodes`

**Nodes Collection**

List all actual nodes.

*Nickname:* `getNodes`  
*Returns:* array[`Node`]

### Models

#### `Device`

LON Device

| Property | Type | Description |
| -------- | ---- | ----------- |
| `deviceClass` | string |  |
| `id` | integer |  |
| `name` | string |  |
| `protocol` | string |  |

#### `Error`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `code` | integer |  |
| `fileds` | string |  |
| `message` | string |  |

#### `Node`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `devices` | array[`Device`] |  |
| `name` | string |  |
| `neuronId` | string |  |
| `nodeId` | integer | id of the node |
| `programId` | string |  |
| `subnet` | integer |  |

#### `Status`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `code` | integer |  |
| `message` | string |  |

### `GET /api/1.0/object`

**Retrieve OID Object**

Retrieve one OID or a list of OID's

*Nickname:* `getObject`  
*Returns:* Object

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `OID` | query | string | yes | The `OID` of the Object to perform action with.<br/>For a list of OID's use comma separated values format (csv). |
| `cacheCtl` | query | integer | no | cache control 0: no cache do bypass the cache, 1: with cache (default) |

### `PUT /api/1.0/object`

**Update OID object**

Update OID Object.

*Nickname:* `putObject`  
*Returns:* Status

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `OID` | body | Object | yes | The `OID` of the Object to perform action with. |

### Models

#### `Error`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `code` | integer |  |
| `message` | string |  |

#### `Object`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `OID` | string | OID of the Object |
| `subtypeId` | integer | for LongStruct this is the LngStrId |
| `timestamp` | string |  |
| `typeId` | integer |  |
| `value` | object |  |

#### `Status`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `code` | integer |  |
| `message` | string |  |

### `GET /api/1.0/scan/nodes/model`

**scan model**

Retrieve scan model.

*Nickname:* `getScanNodesModel`  
*Returns:* void

### `PUT /api/1.0/scan/nodes/model`

**scan model**

Retrieve scan model.

*Nickname:* `putScanNodesModel`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `lonScanModel` | body | LonScanModel | yes | The `LonScanModel` of the Object to perform action with. |

### `GET /api/1.0/scan/nodes/status`

**scan status**

Retrieve scan status.

*Nickname:* `getScanNodesStatus`  
*Returns:* void

### `PUT /api/1.0/scan/nodes/{cmd}`

**LonScanStateMachine commands.**

LonScanStateMachine commands.

*Nickname:* `putScanNodesCmd`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `cmd` | path | string | yes | cmd to be posted. |

### `GET /api/1.0/scan/nvcount/{subnetId}/{nodeId}`

**get nvcount from a Node**

get nvcount from a Node.

*Nickname:* `getScanNv`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `subnetId` | path | integer | yes | Numeric `id` of the subnet to perform action with. (for RC7030 it is always 1). |
| `nodeId` | path | integer | yes | Numeric `id` of the `Node` to perform action with. |

### `GET /api/1.0/scan/nvstruct/{subnetId}/{nodeId}`

**get nvstruct from a Node**

get nvstruct from a Node.

*Nickname:* `getScanNv`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `subnetId` | path | integer | yes | Numeric `id` of the subnet to perform action with. (for RC7030 it is always 1). |
| `nodeId` | path | integer | yes | Numeric `id` of the `Node` to perform action with. |

### `GET /api/1.0/scan/nv/{subnetId}/{nodeId}`

**scan NVs from a Node**

scan NVs from a Node.

*Nickname:* `getScanNv`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `subnetId` | path | integer | yes | Numeric `id` of the subnet to perform action with. (for RC7030 it is always 1). |
| `nodeId` | path | integer | yes | Numeric `id` of the `Node` to perform action with. |

### Models

#### `Error`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `code` | integer |  |
| `fileds` | string |  |
| `message` | string |  |

#### `Function`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `fctId` | integer | id of the function |
| `fctType` | integer |  |
| `lock` | bool |  |
| `name` | string |  |

#### `Level`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `count` | integer | number of the datapoints inside this level |
| `id` | integer | id of the level |

#### `LonNode`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `neuronId` | string |  |
| `nodeId` | integer | id of the node |
| `programId` | string |  |
| `subnet` | integer | id of the subnet |

#### `LonScanModel`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `auto` | boolean | auto mode |
| `groups` | string | list of groups to scan seperator by comma |
| `verbose` | boolean | verbose mode |

#### `Node`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `functions` | array[`Function`] |  |
| `name` | string |  |
| `neuronId` | string |  |
| `nodeId` | integer | id of the node |
| `programId` | string |  |
| `subnet` | integer |  |

#### `Status`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `code` | integer |  |
| `message` | string |  |

#### `Subnet`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `id` | integer | id of the subnet |
| `name` | string | name of the subnet |

### `GET /api/1.0/settings`

**get settings list**

Returns a list of all key-value pairs.

*Nickname:* `getList`  
*Returns:* void

### `GET /api/1.0/settings/allKeys`

**get list af all keys**

Returns a list of all keys, including subkeys, that can be read using this service.

*Nickname:* `getAllKeys`  
*Returns:* void

### `GET /api/1.0/settings/{key}`

**get settings value from key**

get settings value from key

*Nickname:* `getKeyValue`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `key` | path | string | yes | settings key. |

### `PUT /api/1.0/settings/{key}`

**update value value for key**

update value value for key

*Nickname:* `putKeyValue`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `key` | path | string | yes | settings key. |
| `value` | query | string | yes | value for key. |

### `PUT /api/1.0/settings/logging/level`

**update logging level**

update logging level

*Nickname:* `putLoggingLevel`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `value` | query | string | yes | level id to be updated. |

### Models

#### `INFO`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `name` | string |  |
| `version` | string |  |

#### `SettingsModel`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `key` | string |  |
| `value` | string |  |

### `GET /api/1.0/user/users`

**Retrieve all users**

This can only be done by the logged in user.

*Nickname:* `getUsers`  
*Returns:* void

### `GET /api/1.0/user/groups`

**Retrieve all groups**

This can only be done by the logged in user.

*Nickname:* `getGroups`  
*Returns:* void

### `GET /api/1.0/user/group/{groupname}`

**Retrieve group**

This can only be done by the logged in user.

*Nickname:* `getGroup`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `groupname` | path | string | yes | goup name to be retrieve |

### `POST /api/1.0/user/group/{groupname}`

**Add user to group**

This can only be done by the logged in user.

*Nickname:* `addUserToGroup`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `groupname` | path | string | yes | goup name to insert user |
| `username` | query | string | yes | username to insert into groupname |

### `DELETE /api/1.0/user/group/{groupname}`

**Delete user from group**

This can only be done by the logged in user.

*Nickname:* `deleteUserFromGroup`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `groupname` | path | string | yes | goup name from where the user will be deleted. |
| `username` | query | string | yes | username to delete from groupname |

### `POST /api/1.0/user`

**Create user**

This can only be done by the logged in user.

*Nickname:* `createUser`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `body` | body | User | yes | Created user object |

### `PUT /api/1.0/user`

**Updated user**

This can only be done by the logged in user.

*Nickname:* `updateUser`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `body` | body | User | yes | user object to be updated (username and password are required) |

### `DELETE /api/1.0/user/{username}`

**Delete user**

This can only be done by the logged in user.

*Nickname:* `deleteUser`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `username` | path | string | yes | The username that needs to be deleted |

### `GET /api/1.0/user/{username}`

**Get user by user name**

*Nickname:* `getUserByName`  
*Returns:* User

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `username` | path | string | yes | The name that needs to be fetched. |

### `GET /api/1.0/user/login`

**Logs user into the system**

*Nickname:* `loginUser`  
*Returns:* string

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `username` | query | string | yes | The user name for login |
| `password` | query | string | yes | The password for login in clear text |

### `GET /api/1.0/user/logout`

**Logs out current logged in user session**

*Nickname:* `logoutUser`  
*Returns:* void

### Models

#### `User`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `email` | string |  |
| `firstName` | string |  |
| `id` | integer |  |
| `lastName` | string |  |
| `password` | string |  |
| `phone` | string |  |
| `userStatus` | integer | User Status |
| `username` | string |  |

### `DELETE /api/1.0/vpn/key`

**Löscht den aktuellen Key**

*Nickname:* `deleteKey`  
*Returns:* void

### `POST /api/1.0/vpn/key`

**Generiert einen neuen Key**

*Nickname:* `postKey`  
*Returns:* void

### `GET /api/1.0/vpn/csr`

**Gibt das aktuelle erstelle CSR zurück**

*Nickname:* `getCsr`  
*Returns:* void

### `POST /api/1.0/vpn/csr`

**Erzeugt einen neuen CSR**

*Nickname:* `postCsr`  
*Returns:* void

### `PUT /api/1.0/vpn/csr`

**Sendet das CSR zur VPN API**

*Nickname:* `postCsr`  
*Returns:* void

### `GET /api/1.0/vpn/crt`

**Ladet das erstellte CRT herunter und speichert es ab**

*Nickname:* `getCrt`  
*Returns:* void

### `DELETE /api/1.0/vpn/crt`

**Löscht das aktuelle Zertifikat**

*Nickname:* `deleteKey`  
*Returns:* void

### `GET /api/1.0/vpn/status`

**Gibt den aktuellen status der VPN API zurück**

*Nickname:* `getStatus`  
*Returns:* void

### `POST /api/1.0/vpn/mac`

**Überschreibt die aktuelle MAC Adresse (temporär)**

*Nickname:* `postMAC`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `updateMACModel` | body | updateMACModel | yes | updateMACModel as JSON |

### Models

#### `User`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `email` | string |  |
| `firstName` | string |  |
| `id` | integer |  |
| `lastName` | string |  |
| `password` | string |  |
| `phone` | string |  |
| `userStatus` | integer | User Status |
| `username` | string |  |

#### `updateMACModel`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `mac` | string | MAC Address formated as 'hh:hh:hh:hh:hh:hh' |

## WsAdmin v1.0 *(used by integration)*

### `GET /WsAdmin/api/1.0/info/{id}`

**Retrieve id info**

Retrieve id info

*Nickname:* `getInfoId`  
*Returns:* InfoModel

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `id` | path | string | yes | Info id to be retrieve |

### Models

#### `InfoModel`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `name` | string |  |
| `version` | string |  |

### `GET /WsAdmin/api/1.0/led`

**LED Collection**

List of all <b>LEDs<b> on the BSP.

*Nickname:* `getLed`  
*Returns:* array[`LedModel`]

### `GET /WsAdmin/api/1.0/led/{id}`

**Retrieve LED status**

Retrieve LED object

*Nickname:* `getLedId`  
*Returns:* LedModel

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `id` | path | string | yes | LED id to be retrieve |

### `PUT /WsAdmin/api/1.0/led/{id}`

**Update LED**

Update LED

*Nickname:* `putLedId`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `id` | path | string | yes | LED id to be updated |
| `rate` | query | integer | yes | rate |
| `msPeriod` | query | integer | no | period in milli seconds |

### `GET /WsAdmin/api/1.0/led/scene`

**old interface**

do not use his old interface type!

*Nickname:* `getLedScene`  
*Returns:* LedsSceneModel

### `PUT /WsAdmin/api/1.0/led/scene/{id}`

**update LED scene**

Update LED scene.

*Nickname:* `putLedSceneId`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `id` | path | string | yes | Scene id to be set |

### Models

#### `LedModel`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `id` | string | LED id |
| `msPeriod` | integer |  |
| `rate` | integer |  |

#### `LedsSceneModel`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `id` | string | LED scene id |

### `GET /WsAdmin/api/1.0/settings`

**get settings list**

Returns a list of all key-value pairs.

*Nickname:* `getList`  
*Returns:* void

### `GET /WsAdmin/api/1.0/settings/allKeys`

**get list af all keys**

Returns a list of all keys, including subkeys, that can be read using this service.

*Nickname:* `getAllKeys`  
*Returns:* void

### `GET /WsAdmin/api/1.0/settings/{key}`

**get settings value from key**

get settings value from key

*Nickname:* `getKeyValue`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `key` | path | string | yes | settings key. |

### `PUT /WsAdmin/api/1.0/settings/{key}`

**update value value for key**

update value value for key

*Nickname:* `putKeyValue`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `key` | path | string | yes | settings key. |
| `value` | query | string | yes | value for key. |

### `PUT /WsAdmin/api/1.0/settings/logging/level`

**update logging level**

update logging level

*Nickname:* `putLoggingLevel`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `value` | query | string | yes | level id to be updated. |

### Models

#### `INFO`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `name` | string |  |
| `version` | string |  |

#### `SettingsModel`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `key` | string |  |
| `value` | string |  |

### `GET /WsAdmin/api/1.0/systemtime`

**get current systemtime [ISO 8601]**

get current systemtime [Internet Date/Time Format][ISO 8601]

*Nickname:* `getSystemtime`  
*Returns:* void

### `PUT /WsAdmin/api/1.0/systemtime`

**update systemtime**

update systemtime

*Nickname:* `putSystemtime`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `value` | query | string | yes | value for systemtime [Internet Date/Time Format] [ISO 8601] |

### `GET /WsAdmin/api/1.0/systemtime/ntpserver`

**Retrieve ntp server list**

Retrieve ntp server list

*Nickname:* `getNtpServerList`  
*Returns:* void

### `POST /WsAdmin/api/1.0/systemtime/ntpserver`

**Add new ntp server item**

Add new ntp server item

*Nickname:* `postNtpServer`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `hostname` | query | string | yes | The `hostname` to perform action with. |

### `GET /WsAdmin/api/1.0/systemtime/ntpserver/selected`

**get selected ntp server**

get selected ntp server

*Nickname:* `getNtpServerSelected`  
*Returns:* void

### `GET /WsAdmin/api/1.0/systemtime/ntpserver/{id}`

**Retrieve ntp server at 'id'**

Retrieve ntp server ad 'id'

*Nickname:* `getNtpServerId`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `id` | path | integer | yes | id to perform action with. |

### `DELETE /WsAdmin/api/1.0/systemtime/ntpserver/{id}`

**Delete ntp server at 'id'**

Delete ntp server ad 'id'

*Nickname:* `deleteNtpServerAtId`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `id` | path | integer | yes | id to perform action with. |

### `PUT /WsAdmin/api/1.0/systemtime/ntpserver/select/{id}`

**Update ntpserver.selected at 'id'**

Update ntpserver.selected ad 'id'

*Nickname:* `putNtpServerSelectId`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `id` | path | integer | yes | id to perform action with. |

### `GET /WsAdmin/api/1.0/systemtime/timezone`

**get current timezone information and timezone list**

*Nickname:* `getTimezone`  
*Returns:* void

### `PUT /WsAdmin/api/1.0/systemtime/timezone`

**update timezone**

update timezone

*Nickname:* `putTimezone`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `value` | query | string | yes | value for systemtime Europe/Paris |

### Models

#### `NtpServerModel`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `hostname` | string |  |
| `selected` | integer |  |

#### `Status`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `code` | integer |  |
| `message` | string |  |

#### `SystemTimeModel`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `dateTime` | string |  |

### `GET /WsAdmin/api/1.0/update/factoryReset`

**Retrieve FactoryReset Status**

Retrieve FactoryReset Status

*Nickname:* `getFactoryReset`  
*Returns:* void

### `PUT /WsAdmin/api/1.0/update/factoryReset/{method}`

**Factory Reset methods**

Factory Reset methods

*Nickname:* `putFactoryResetMethod`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `method` | path | string | yes | method to perform action with. |

### `GET /WsAdmin/api/1.0/update/firmware/{method}`

**Retrieve firmware info**

Retrieve firmware info.

*Nickname:* `getUpdateFirmware`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `method` | path | string | yes | command |

### `PUT /WsAdmin/api/1.0/update/firmware/{method}`

**update firmware operations**

update firmware operations.

*Nickname:* `postUpdateFirmware`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `method` | path | string | yes | command |
| `body` | body | UpdateOld | yes | update object |

### `POST /WsAdmin/api/1.0/update/firmware/{method}`

**Retrieve firmware**

Old format do not use it in the future.

*Nickname:* `postUpdateFirmware`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `method` | path | string | yes | command |
| `body` | body | UpdateOld | yes | update object |

### Models

#### `Update`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `email` | string |  |
| `firstName` | string |  |
| `id` | integer |  |
| `lastName` | string |  |
| `password` | string |  |
| `phone` | string |  |
| `userStatus` | integer | User Status |
| `username` | string |  |

#### `UpdateOld`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `bytesReceived` | integer |  |
| `bytesTotal` | integer |  |
| `cmd` | string | command for old interface |
| `status` | string |  |

### `GET /WsAdmin/api/1.0/user/login`

**Logs user into the system**

*Nickname:* `loginUser`  
*Returns:* string

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `username` | query | string | yes | The user name for login |
| `password` | query | string | yes | The password for login in clear text |

### `GET /WsAdmin/api/1.0/user/logout`

**Logs out current logged in user session**

*Nickname:* `logoutUser`  
*Returns:* void

### Models

#### `User`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `email` | string |  |
| `firstName` | string |  |
| `id` | integer |  |
| `lastName` | string |  |
| `password` | string |  |
| `phone` | string |  |
| `userStatus` | integer | User Status |
| `username` | string |  |

## WsFUP7030 v1.0

### `GET /WsFUP7030/api/1.0/LON/nodeAddress/{domainIdx}`

**get nodeAdress**

get nodeAdress

*Nickname:* `getLONNodeAddress`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `domainIdx` | path | integer | yes | index of domain to be retrieve |

### `PUT /WsFUP7030/api/1.0/LON/nviTimeSet/{year}/{month}/{day}/{hour}/{min}/{sec}`

**update nviTimeSet**

update nviTimeSet

*Nickname:* `putLONnviTimeSet`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `year` | path | integer | yes | year: 0..3000  0 means year not specified. 65535 represents null date |
| `month` | path | integer | yes | month:  0..12    0 means month not specified |
| `day` | path | integer | yes | day: 0..31    0 means day not specified |
| `hour` | path | integer | yes | hour: 0..23 |
| `min` | path | integer | yes | min: 0..59 |
| `sec` | path | integer | yes | sec: 0..59 |

### `PUT /WsFUP7030/api/1.0/LON/msg`

**Send msg Services (ACKD or UNACK)**

Send msg Services (ACKD or UNACK)

*Nickname:* `putLonMsg`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `body` | body | LonMsgOut | yes | LON Msg object to action on. |

### `POST /WsFUP7030/api/1.0/LON/msg`

**Request/Response msg Services**

Request/Response msg Services

*Nickname:* `postLonMsg`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `body` | body | LonMsgOut | yes | LON Msg object to action on. |

### `PUT /WsFUP7030/api/1.0/LON/NMPDU`

**Network Management Services (ACKD or UNACK)**

Network Management Services (ACKD or UNACK)

*Nickname:* `putLonNMPDU`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `body` | body | NMPDUrequest | yes | PDU object to action on. |

### `POST /WsFUP7030/api/1.0/LON/NMPDU`

**Network Management Services**

Network Management Services

*Nickname:* `postLonNMPDU`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `body` | body | NMPDUrequest | yes | PDU object to action on. |

### `POST /WsFUP7030/api/1.0/LON/NMPDU/QueryID/{group}/{selector}`

**Network Management Query ID**

Network Management Query ID

*Nickname:* `postNMPDUQueryID`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `group` | path | integer | yes | Destination group address. |
| `selector` | path | integer | yes | selector: <br/>0 = unconfigured nodes<br/>1 = respond to query set<br/>2 = 0 and 1 |

### `PUT /WsFUP7030/api/1.0/LON/NMPDU/RespondToQuery/group/{groupId}/{mode}`

**Network Management Respond to Query (UNACKD)**

Network Management Respond to Query (UNACKD)

*Nickname:* `putNMPDUespondToQueryGroup`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `groupId` | path | integer | yes | Destination group address. |
| `mode` | path | integer | yes | 1 => ON; 0 => OFF. |

### `POST /WsFUP7030/api/1.0/LON/NMPDU/RespondToQuery/group/{groupId}/{mode}`

**Network Management Respond to Query**

Network Management Respond to Query

*Nickname:* `postNMPDUespondToQueryGroup`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `groupId` | path | integer | yes | Destination group address. |
| `mode` | path | integer | yes | 1 => ON; 0 => OFF. |

### `POST /WsFUP7030/api/1.0/LON/NMPDU/RespondToQuery/snode/{subnet}/{nodeId}/{mode}`

**Network Management Respond to Query**

Network Management Respond to Query

*Nickname:* `postNMPDUespondToQuerySnode`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `subnet` | path | integer | yes | Numeric `id` of the subnet to perform action with. (for RC7030 it is always 1). |
| `nodeId` | path | integer | yes | Numeric `id` of the `Node` to perform action with. |
| `mode` | path | integer | yes | 1 => ON; 0 => OFF. |

### `PUT /WsFUP7030/api/1.0/LON/NMPDU/RespondToQuery/neuronId`

**Network Management Respond to Query (UNACKD)**

Network Management Respond to Query (UNACKD)

*Nickname:* `putNMPDUespondToQueryNeuronId`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `neuronId` | query | string | yes | neuronID as target address. |
| `mode` | query | integer | yes | 1 => ON; 0 => OFF. |

### `POST /WsFUP7030/api/1.0/LON/NMPDU/RespondToQuery/neuronId`

**Network Management Respond to Query**

Network Management Respond to Query

*Nickname:* `postNMPDUespondToQueryNeuronId`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `neuronId` | query | string | yes | neuronID as target address. |
| `mode` | query | integer | yes | 1 => ON; 0 => OFF. |

### `GET /WsFUP7030/api/1.0/LON/NMPDU/QueryAddress/{subnet}/{nodeId}/{index}`

**NMPDU Query Address**

NMPDU Query Address

*Nickname:* `getNMPDUQueryAddress`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `subnet` | path | integer | yes | Numeric `id` of the subnet to perform action with. (for RC7030 it is always 1). |
| `nodeId` | path | integer | yes | Numeric `id` of the `Node` to perform action with. |
| `index` | path | integer | yes | Index 0-14. |

### `GET /WsFUP7030/api/1.0/LON/NMPDU/QueryNvConfiguration/{subnet}/{nodeId}/{nvIndex}`

**NMPDU Query Network Variable Configuration**

NMPDU Query Network Variable Configuration

*Nickname:* `getNMPDUQueryNvConfiguration`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `subnet` | path | integer | yes | Numeric `id` of the subnet to perform action with. (for RC7030 it is always 1). |
| `nodeId` | path | integer | yes | Numeric `id` of the `Node` to perform action with. |
| `nvIndex` | path | integer | yes | Network Variable Index. |

### `POST /WsFUP7030/api/1.0/LON/NMPDU/QueryDomain`

**Network Management Query Domain**

Network Management Query Domain

*Nickname:* `postNMPDUQueryDomain`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `body` | body | LonDeviceModel | yes | LonDevice object for target address. |

### `GET /WsFUP7030/api/1.0/LON/NMPDU/QueryDomain`

**Network Management Query Domain**

Network Management Query Domain

*Nickname:* `getNMPDUQueryDomainNID`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `neuronId` | query | string | yes | neuronID as target address. |

### `GET /WsFUP7030/api/1.0/LON/NMPDU/NvValueFetch/{subnet}/{nodeId}/{nvIndex}`

**Network Management Network Variable Value Fetch**

Network Management Network Variable Value Fetch

*Nickname:* `postNMPDUNvValueFetch`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `subnet` | path | integer | yes | Numeric `id` of the subnet to perform action with. (for RC7030 it is always 1). |
| `nodeId` | path | integer | yes | Numeric `id` of the `Node` to perform action with. |
| `nvIndex` | path | integer | yes | Network Variable Index. |

### Models

#### `INFO`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `name` | string |  |
| `version` | string |  |

#### `LonDeviceModel`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `domainIdx` | integer |  |
| `neuronId` | string |  |
| `nodeId` | integer |  |
| `programId` | string |  |
| `subnet` | integer |  |

#### `LonMsgOut`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `address` | array[`integer`] |  |
| `addressMode` | integer |  |
| `code` | integer |  |
| `data` | array[`integer`] |  |
| `service` | integer |  |

#### `NMPDUrequest`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `address` | array[`integer`] |  |
| `addressMode` | integer |  |
| `command` | integer |  |
| `data` | array[`integer`] |  |
| `service` | integer |  |

#### `NodeAdress`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `domainIdx` | integer |  |
| `nodeId` | integer |  |
| `subnet` | integer |  |

### `GET /WsFUP7030/api/1.0/config/nodeAddress/{domainIdx}`

**get nodeAdress**

get nodeAdress

*Nickname:* `getConfigNodeAddress`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `domainIdx` | path | integer | yes | index of domain to be retrieve |

### `PUT /WsFUP7030/api/1.0/config/nodeAddress`

**update nodeAdress**

update nodeAdress

*Nickname:* `putConfigNodeAddress`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `body` | body | NodeAdress | yes | NodeAdress object to be updated. |

### `GET /WsFUP7030/api/1.0/config/lon/bitrate`

**get LON Transceiver Bit Rate**

get bitrate

*Nickname:* `getLonBitRate`  
*Returns:* void

### `PUT /WsFUP7030/api/1.0/config/lon/bitrate`

**update LON Transceiver Bit Rate**

update bitrate

*Nickname:* `putLonBitRate`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `value` | query | string | yes | bitrate to be updated. |

### `GET /WsFUP7030/api/1.0/config/lon/transceiver`

**get LON Tranceiver config data**

get partial config data

*Nickname:* `getLonTransceiver`  
*Returns:* void

### `PUT /WsFUP7030/api/1.0/config/lon/transceiver`

**update LON Tranceiver config data**

update partial config data (channle_id is readonly!)

*Nickname:* `putLonTransceiver`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `body` | body | LonTransceiver | yes | LonTransceiver object to be updated. |

### `PUT /WsFUP7030/api/1.0/config/lon/swreset`

**Software Reset on LON Chip**

send cmd to reset the Neuron

*Nickname:* `putLonSwReset`  
*Returns:* void

### Models

#### `INFO`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `name` | string |  |
| `version` | string |  |

#### `LonTransceiver`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `channel_id` | integer |  |
| `comm_clock` | integer |  |
| `input_clock` | integer |  |

#### `NodeAdress`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `domainIdx` | integer |  |
| `nodeId` | integer |  |
| `subnet` | integer |  |

### `GET /WsFUP7030/api/1.0/hwtest/fup`

**Retrieve id info**

Retrieve id info

*Nickname:* `getHwTestFup`  
*Returns:* void

### `GET /WsFUP7030/api/1.0/hwtest/lop/{id}`

**Retrieve LOP App info**

Retrieve LOP App info

*Nickname:* `getHwTestLopId`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `id` | path | string | yes | id to be retrieve |

### `PUT /WsFUP7030/api/1.0/hwtest/lop/brdcstLock`

**Set Broadcast Lock**

Set Broadcast Lock

*Nickname:* `putHwTestLopBrdcstLock`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `value` | query | integer | no | Numeric `timeout` in 0.1 seconds. (0 or none: forever) |

### Models

#### `INFO`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `name` | string |  |
| `version` | string |  |

### `GET /WsFUP7030/api/1.0/info/{id}`

**Retrieve id info**

Retrieve id info

*Nickname:* `getInfoId`  
*Returns:* InfoModel

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `id` | path | string | yes | Info id to be retrieve |

### Models

#### `InfoModel`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `name` | string |  |
| `version` | string |  |

### `PUT /WsFUP7030/api/1.0/led`

**update LED object**

Update LED with information in the object body.

*Nickname:* `putLed`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `body` | body | LED | yes | LED object to be updated |

### `GET /WsFUP7030/api/1.0/led/{id}`

**Retrieve LED status**

Retrieve LED object

*Nickname:* `getLedId`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `id` | path | string | yes | LED id to be retrieve |

### `PUT /WsFUP7030/api/1.0/led/{id}`

**Update LED**

Update LED

*Nickname:* `putLedId`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `id` | path | string | yes | LED id to be updated |
| `rate` | query | integer | yes | rate |
| `msPeriod` | query | integer | no | period in milli seconds |

### `GET /WsFUP7030/api/1.0/led/scene`

**retrieve LED scene**

retrieve LED scene

*Nickname:* `getLedScene`  
*Returns:* void

### `PUT /WsFUP7030/api/1.0/led/scene/{id}`

**update LED scene**

Update LED scene.

*Nickname:* `putLedSceneId`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `id` | path | string | yes | Scene id to be set |

### Models

#### `LED`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `id` | string | LED id |
| `msPeriod` | integer |  |
| `rate` | integer |  |

#### `LEDold`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `cmd` | string | command for old interface |
| `id` | string | LED id |
| `msPeriod` | integer |  |
| `rate` | integer |  |

### `POST /WsFUP7030/api/1.0/lonscan/test/{step}`

**Retrieve test**

Retrieve test

*Nickname:* `postLonscanTest`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `step` | path | string | yes | step id to be retrieve |

### `POST /WsFUP7030/api/1.0/lonscan/run`

**run lonscan**

run lonscan

*Nickname:* `postLonscanRun`  
*Returns:* void

### Models

#### `INFO`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `name` | string |  |
| `version` | string |  |

### `POST /WsFUP7030/api/1.0/notification/register`

**register for a new notification**

register for a new notification

*Nickname:* `postNotificationRegister`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `body` | body | RegisterNotificationModel | yes | NotificationModel object to action on. |

### `POST /WsFUP7030/api/1.0/notification/unregister`

**unregister the notification**

register the notification

*Nickname:* `postNotificationUnregister`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `body` | body | UnregisterNotificationModel | yes | Notification UUID received on registration. |

### Models

#### `RegisterNotificationModel`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `endpoint` | string |  |
| `method` | string |  |
| `service` | string |  |
| `uri` | string |  |

#### `UnregisterNotificationModel`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `UUID` | string |  |

### `GET /WsFUP7030/api/1.0/settings`

**get settings list**

Returns a list of all key-value pairs.

*Nickname:* `getList`  
*Returns:* void

### `GET /WsFUP7030/api/1.0/settings/allKeys`

**get list af all keys**

Returns a list of all keys, including subkeys, that can be read using this service.

*Nickname:* `getAllKeys`  
*Returns:* void

### `GET /WsFUP7030/api/1.0/settings/{key}`

**get settings value from key**

get settings value from key

*Nickname:* `getKeyValue`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `key` | path | string | yes | settings key. |

### `PUT /WsFUP7030/api/1.0/settings/{key}`

**update value value for key**

update value value for key

*Nickname:* `putKeyValue`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `key` | path | string | yes | settings key. |
| `value` | query | string | yes | value for key. |

### `PUT /WsFUP7030/api/1.0/settings/logging/level`

**update logging level**

update logging level

*Nickname:* `putLoggingLevel`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `value` | query | string | yes | level id to be updated. |

### Models

#### `INFO`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `name` | string |  |
| `version` | string |  |

#### `SettingsModel`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `key` | string |  |
| `value` | string |  |

### `GET /WsFUP7030/api/1.0/srv0620`

**Retrieve srv0620**

Retrieve srv0620

*Nickname:* `getSrv0620`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `oid` | query | string | no | OID as /subnet/nodeId/fnctNbr/levelIdx. |

### `POST /WsFUP7030/api/1.0/srv0620`

**Retrieve srv0620**

Retrieve srv0620

*Nickname:* `postSrv0620`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `body` | body | Srv0620request | yes | Srv0620 object to action on. |

### `GET /WsFUP7030/api/1.0/srv0620/{subnet}/{nodeId}/{fnctNbr}/{levelIdx}`

**Retrieve srv0620**

Retrieve srv0620

*Nickname:* `getSrv0620Path`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `subnet` | path | integer | yes | Numeric `id` of the subnet to perform action with. (for RC7030 it is always 1). |
| `nodeId` | path | integer | yes | Numeric `id` of the `Node` to perform action with. |
| `fnctNbr` | path | integer | yes | Numeric `id` of the `Function` to perform action with. |
| `levelIdx` | path | integer | yes | Numeric `id` of the `Level` to perform action with. |

### Models

#### `Srv0620request`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `fnctNbr` | integer |  |
| `levelIdx` | integer |  |
| `nodeId` | integer |  |
| `subnet` | integer |  |

### `POST /WsFUP7030/api/1.0/srv0621`

**Retrieve srv0621**

Retrieve srv0621

*Nickname:* `postSrv0621`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `body` | body | Srv0621request | yes | Srv0621 object to action on. |

### `GET /WsFUP7030/api/1.0/srv0621/{subnet}/{nodeId}/{mainSel}/{subSel}`

**Retrieve srv0621**

Retrieve srv0621

*Nickname:* `getSrv0621Path`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `subnet` | path | integer | yes | Numeric `id` of the subnet to perform action with. (for RC7030 it is always 1). |
| `nodeId` | path | integer | yes | Numeric `id` of the `Node` to perform action with. |
| `mainSel` | path | string | yes | MainSelector to perform action with. [WORD] in hex-format |
| `subSel` | path | string | yes | SubSelector to perform action with. [WORD] in hex-format |

### Models

#### `Srv0621request`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `mainSel` | string |  |
| `nodeId` | integer |  |
| `subSel` | string |  |
| `subnet` | integer |  |

### `POST /WsFUP7030/api/1.0/srv0622`

**Retrieve srv0622**

Retrieve srv0622

*Nickname:* `postSrv0622`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `body` | body | Srv0622request | yes | Srv0622 object to action on. |

### `GET /WsFUP7030/api/1.0/srv0622/{subnet}/{nodeId}/{mainSel}/{subSel}`

**Retrieve srv0622**

Retrieve srv0622

*Nickname:* `getSrv0622Path`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `subnet` | path | integer | yes | Numeric `id` of the subnet to perform action with. (for RC7030 it is always 1). |
| `nodeId` | path | integer | yes | Numeric `id` of the `Node` to perform action with. |
| `mainSel` | path | string | yes | MainSelector to perform action with. [WORD] in hex-format |
| `subSel` | path | string | yes | SubSelector to perform action with. [WORD] in hex-format |

### Models

#### `Srv0622request`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `mainSel` | string |  |
| `nodeId` | integer |  |
| `subSel` | string |  |
| `subnet` | integer |  |

### `PUT /WsFUP7030/api/1.0/srv0623`

**Write srv0623 with OID**

Write srv0623 with OID and value

*Nickname:* `putSrv0623OidValue`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `oid` | query | string | yes | OID as /subnet/nodeId/fctId/group/member/instance. |
| `value` | query | string | yes | value decimal or hex with prepanding 0x |

### `POST /WsFUP7030/api/1.0/srv0623`

**Write srv0623 with body**

Write srv0623 with body

*Nickname:* `postSrv0623`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `body` | body | Srv0623Model | yes | Srv0623Model object to perform action. |

### Models

#### `INFO`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `name` | string |  |
| `version` | string |  |

#### `Srv0623Model`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `data` | array[`integer`] |  |
| `mainSel` | string |  |
| `nodeId` | integer |  |
| `subSel` | string |  |
| `subnet` | integer |  |

### `GET /WsFUP7030/api/1.0/srv1024/{subnetId}/{nodeId}/{fctId}/{groupId}/{memberId}/{varInst}`

**Retrieve Datapoint**

A single Datapoint object with all its details (identifikationsgesz. DP)

*Nickname:* `getSrv1024`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `subnetId` | path | integer | yes | Numeric `id` of the subnet to perform action with. (for RC7030 it is always 1). |
| `nodeId` | path | integer | yes | Numeric `id` of the `Node` to perform action with. |
| `fctId` | path | integer | yes | Numeric `id` of the `Function` to perform action with. |
| `groupId` | path | integer | yes | Numeric `id` of the `Group` to perform action with. |
| `memberId` | path | integer | yes | Numeric `id` of the `memberId` to perform action with. |
| `varInst` | path | integer | no | Numeric `id` of the `varInst` to perform action with. (default 0) |

### Models

#### `InfoModel`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `name` | string |  |
| `version` | string |  |

### `PUT /WsFUP7030/api/1.0/srv1025`

**Put srv0623 with OID**

Put srv0623 with OID and value

*Nickname:* `putSrv0623OidValue`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `oid` | query | string | yes | OID as /subnet/nodeId/fctId/group/member/instance. |
| `value` | query | string | yes | value decimal or hex with prepanding 0x |

### Models

#### `InfoModel`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `name` | string |  |
| `version` | string |  |

### `PUT /WsFUP7030/api/1.0/windyndata/{subnetId}/{nodeId}/1/{DapId}/{value}`

**windyndata WriteDap**

windyndata WriteDap

*Nickname:* `putWindyndataWriteDapDapIdVal1`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `subnet` | path | integer | yes | Numeric `id` of the subnet to perform action with. (for RC7030 it is always 1). |
| `nodeId` | path | integer | yes | Numeric `id` of the `Node` to perform action with. |
| `DapId` | path | integer | yes | Numeric `id` of the `DAP` to perform action with. |
| `value` | path | integer | yes | value to perform action with. |

### `GET /WsFUP7030/api/1.0/windyndata/{subnetId}/{nodeId}/2/{DapId}`

**windyndata ReadDap**

windyndata ReadDap

*Nickname:* `getWindyndataReadDapDapId`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `subnet` | path | integer | yes | Numeric `id` of the subnet to perform action with. (for RC7030 it is always 1). |
| `nodeId` | path | integer | yes | Numeric `id` of the `Node` to perform action with. |
| `DapId` | path | integer | yes | Numeric `id` of the `DAP` to perform action with. |

### `GET /WsFUP7030/api/1.0/windyndata/{subnetId}/{nodeId}/3/{FctSel}`

**Read windyndata FctCall**

Read windyndata FctCall

*Nickname:* `getWindyndataFctCallFctSel`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `subnet` | path | integer | yes | Numeric `id` of the subnet to perform action with. (for RC7030 it is always 1). |
| `nodeId` | path | integer | yes | Numeric `id` of the `Node` to perform action with. |
| `FctSel` | path | string | yes | Function selector to perform action with. |

### `PUT /WsFUP7030/api/1.0/windyndata/{subnetId}/{nodeId}/3/{FctSel}/{Param}`

**Write windyndata FctCall**

Write windyndata FctCall

*Nickname:* `putWindyndataFctCallFctSelVal1`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `subnet` | path | integer | yes | Numeric `id` of the subnet to perform action with. (for RC7030 it is always 1). |
| `nodeId` | path | integer | yes | Numeric `id` of the `Node` to perform action with. |
| `FctSel` | path | string | yes | Function selector to perform action with. |
| `Param` | path | integer | yes | Parameter to perform action with. |

### `PUT /WsFUP7030/api/1.0/windyndata/{subnetId}/{nodeId}/3/{FctSel}/{k}/{value}`

**Write windyndata FctCall**

Write windyndata FctCall

*Nickname:* `putWindyndataFctCallFctSelVal1Val2`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `subnet` | path | integer | yes | Numeric `id` of the subnet to perform action with. (for RC7030 it is always 1). |
| `nodeId` | path | integer | yes | Numeric `id` of the `Node` to perform action with. |
| `FctSel` | path | string | yes | Function selector to perform action with. |
| `k` | path | integer | yes | Parameter k (logischer Ausgang) to perform action with. |
| `value` | path | integer | yes | Value to perform action with. |

### `PUT /WsFUP7030/api/1.0/windyndata`

**Write windyndata with body**

Write windyndata with body

*Nickname:* `putWindyndata`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `body` | body | WinDynDataModel | yes | WinDataModel object to perform action. |

### Models

#### `WinDynDataModel`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `DapId` | integer |  |
| `FctId` | integer |  |
| `FctSel` | integer |  |
| `data` | array[`integer`] |  |
| `nodeId` | integer |  |
| `subnet` | integer |  |

### `GET /WsFUP7030/api/1.0/winservice/{subnetId}/{nodeId}/{code}/{subcode}`

**Retrieve winservice**

Retrieve winservice

*Nickname:* `getWinservice`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `subnet` | path | integer | yes | Numeric `id` of the subnet to perform action with. (for RC7030 it is always 1). |
| `nodeId` | path | integer | yes | Numeric `id` of the `Node` to perform action with. |
| `code` | path | string | yes | `code` in HEX formatlike 0x25. |
| `subcode` | path | string | yes | `subcode` in HEX format like 0x01 |

### `PUT /WsFUP7030/api/1.0/winservice`

**update winservice object**

update winservice object

*Nickname:* `putWinservice`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `body` | body | WriteWinServiceModel | yes | WinServiceModel object to be updated. |

### Models

#### `INFO`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `name` | string |  |
| `version` | string |  |

#### `WriteWinServiceModel`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `code` | string |  |
| `data` | array[`integer`] |  |
| `nodeId` | integer |  |
| `subcode` | string |  |
| `subnet` | integer |  |

## dprecorder v1.0

### `GET /dprecorder/api/1.0/info/{id}`

**Retrieve id info**

Retrieve id info

*Nickname:* `getInfoId`  
*Returns:* InfoModel

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `id` | path | string | yes | Info id to be retrieve |

### Models

#### `InfoModel`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `name` | string |  |
| `version` | string |  |

### `GET /dprecorder/api/1.0/recorder/{id}`

**Retrieve id recorder**

Retrieve id recorder

*Nickname:* `getInfoId`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `id` | path | string | yes | Info id to be retrieve |

### `PUT /dprecorder/api/1.0/recorder/{id}`

**Retrieve id recorder**

Retrieve id recorder

*Nickname:* `getInfoId`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `id` | path | string | yes | id to update |
| `value` | query | string | yes | value for id. |

### `POST /dprecorder/api/1.0/recorder/{action}`

**Manualy trigger executing the actionSet**

Manualy trigger executing the actionSet

*Nickname:* `postRecorderAction`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `action` | path | string | yes | Info id to be retrieve |

### `POST /dprecorder/api/1.0/recorder/datapoint`

**Add new OID Datapoint**

Add new OID Datapoint

*Nickname:* `postRecorderOid`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `name` | query | string | yes | Name of the Datapoint |
| `oid` | query | string | yes | OID as /subnet/nodeId/fctId/group/member/instance. |
| `cacheCtl` | query | integer | no | cache control 0: no cache do bypass the cache, 1: with cache (default) |

### `DELETE /dprecorder/api/1.0/recorder/datapoint`

**Delete OID Datapoint**

Delete OID Datapoint

*Nickname:* `deleteRecorderOid`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `oid` | query | string | yes | OID as /subnet/nodeId/fctId/group/member/instance. |

### `DELETE /dprecorder/api/1.0/recorder/oids`

**Delete Recorder OID List**

Delete Recorder OID List

*Nickname:* `deleteRecorderOidList`  
*Returns:* void

### Models

#### `InfoModel`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `name` | string |  |
| `version` | string |  |

### `GET /dprecorder/api/1.0/settings`

**get settings list**

Returns a list of all key-value pairs.

*Nickname:* `getList`  
*Returns:* void

### `GET /dprecorder/api/1.0/settings/allKeys`

**get list af all keys**

Returns a list of all keys, including subkeys, that can be read using this service.

*Nickname:* `getAllKeys`  
*Returns:* void

### `GET /dprecorder/api/1.0/settings/{key}`

**get settings value from key**

get settings value from key

*Nickname:* `getKeyValue`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `key` | path | string | yes | settings key. |

### `PUT /dprecorder/api/1.0/settings/{key}`

**update value value for key**

update value value for key

*Nickname:* `putKeyValue`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `key` | path | string | yes | settings key. |
| `value` | query | string | yes | value for key. |

### `PUT /dprecorder/api/1.0/settings/logging/level`

**update logging level**

update logging level

*Nickname:* `putLoggingLevel`  
*Returns:* void

| Name | In | Type | Required | Description |
| ---- | -- | ---- | -------- | ----------- |
| `value` | query | string | yes | level id to be updated. |

### `POST /dprecorder/api/1.0/settings/reset/all`

**reset all settings**

reset all settings

*Nickname:* `postResetAll`  
*Returns:* void

### Models

#### `INFO`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `name` | string |  |
| `version` | string |  |

#### `SettingsModel`

| Property | Type | Description |
| -------- | ---- | ----------- |
| `key` | string |  |
| `value` | string |  |
