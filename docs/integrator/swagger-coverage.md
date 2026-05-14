# Swagger Coverage Report

Generated from Swagger 1.2 source files in `docs/swagger/`.
Do not edit by hand — run `python scripts/build_docs.py` to regenerate.

## Summary

| Service | Version | Resource | Method | Path | Used by Integration |
| ------- | ------- | -------- | ------ | ---- | ------------------- |
| DcmRC7030 | 1.0 | /info | `GET` | `/DcmRC7030/api/1.0/info/{id}` | no |
| DcmRC7030 | 1.0 | /msg1025 | `PUT` | `/DcmRC7030/api/1.0/msg1025/push` | no |
| DcmRC7030 | 1.0 | /settings | `GET` | `/DcmRC7030/api/1.0/settings` | no |
| DcmRC7030 | 1.0 | /settings | `GET` | `/DcmRC7030/api/1.0/settings/allKeys` | no |
| DcmRC7030 | 1.0 | /settings | `GET` | `/DcmRC7030/api/1.0/settings/{key}` | no |
| DcmRC7030 | 1.0 | /settings | `PUT` | `/DcmRC7030/api/1.0/settings/{key}` | no |
| DcmRC7030 | 1.0 | /settings | `PUT` | `/DcmRC7030/api/1.0/settings/logging/level` | no |
| DcmRC7030 | 1.0 | /settings | `POST` | `/DcmRC7030/api/1.0/settings/reset/all` | no |
| InfoWinFehlerlog | 1.0 | /fehlerlog | `GET` | `/InfoWinFehlerlog/api/1.0/fehlerlog` | no |
| InfoWinFehlerlog | 1.0 | /fehlerlog | `POST` | `/InfoWinFehlerlog/api/1.0/fehlerlog` | no |
| InfoWinFehlerlog | 1.0 | /fehlerlog | `GET` | `/InfoWinFehlerlog/api/1.0/fehlerlog/rawlist` | no |
| InfoWinFehlerlog | 1.0 | /fehlerlog | `GET` | `/InfoWinFehlerlog/api/1.0/fehlerlog/{id}` | no |
| InfoWinFehlerlog | 1.0 | /fehlerlog | `PUT` | `/InfoWinFehlerlog/api/1.0/fehlerlog/{id}` | no |
| InfoWinFehlerlog | 1.0 | /fehlerlog | `DELETE` | `/InfoWinFehlerlog/api/1.0/fehlerlog/{id}` | no |
| InfoWinFehlerlog | 1.0 | /fehlerlog | `PUT` | `/InfoWinFehlerlog/api/1.0/fehlerlog/reset/{id}` | no |
| InfoWinFehlerlog | 1.0 | /fehlerlog | `POST` | `/InfoWinFehlerlog/api/1.0/fehlerlog/{subnetId}/{nodeId}` | no |
| InfoWinFehlerlog | 1.0 | /info | `GET` | `/InfoWinFehlerlog/api/1.0/info/{id}` | no |
| InfoWinFehlerlog | 1.0 | /settings | `GET` | `/InfoWinFehlerlog/api/1.0/settings` | no |
| InfoWinFehlerlog | 1.0 | /settings | `GET` | `/InfoWinFehlerlog/api/1.0/settings/allKeys` | no |
| InfoWinFehlerlog | 1.0 | /settings | `GET` | `/InfoWinFehlerlog/api/1.0/settings/{key}` | no |
| InfoWinFehlerlog | 1.0 | /settings | `PUT` | `/InfoWinFehlerlog/api/1.0/settings/{key}` | no |
| InfoWinFehlerlog | 1.0 | /settings | `PUT` | `/InfoWinFehlerlog/api/1.0/settings/logging/level` | no |
| InfoWinHeartbeat | 1.0 | /heartbeat | `GET` | `/InfoWinHeartbeat/api/1.0/heartbeat` | yes |
| InfoWinHeartbeat | 1.0 | /heartbeat | `POST` | `/InfoWinHeartbeat/api/1.0/heartbeat` | yes |
| InfoWinHeartbeat | 1.0 | /heartbeat | `DELETE` | `/InfoWinHeartbeat/api/1.0/heartbeat` | yes |
| InfoWinHeartbeat | 1.0 | /heartbeat | `PUT` | `/InfoWinHeartbeat/api/1.0/heartbeat/{subnet}/{nodeId}` | yes |
| InfoWinHeartbeat | 1.0 | /info | `GET` | `/InfoWinHeartbeat/api/1.0/info/{id}` | yes |
| InfoWinHeartbeat | 1.0 | /kesselwahl | `GET` | `/InfoWinHeartbeat/api/1.0/kesselwahl/{method}` | yes |
| InfoWinHeartbeat | 1.0 | /kesselwahl | `PUT` | `/InfoWinHeartbeat/api/1.0/kesselwahl/{id}` | yes |
| InfoWinHeartbeat | 1.0 | /kesselwahl | `PUT` | `/InfoWinHeartbeat/api/1.0/kesselwahl/servicepin` | yes |
| InfoWinHeartbeat | 1.0 | /kesselwahl | `GET` | `/InfoWinHeartbeat/api/1.0/kesselwahl/servicepin/listener` | yes |
| InfoWinHeartbeat | 1.0 | /kesselwahl | `POST` | `/InfoWinHeartbeat/api/1.0/kesselwahl/servicepin/listener/{method}` | yes |
| InfoWinHeartbeat | 1.0 | /settings | `GET` | `/InfoWinHeartbeat/api/1.0/settings` | yes |
| InfoWinHeartbeat | 1.0 | /settings | `GET` | `/InfoWinHeartbeat/api/1.0/settings/allKeys` | yes |
| InfoWinHeartbeat | 1.0 | /settings | `GET` | `/InfoWinHeartbeat/api/1.0/settings/{key}` | yes |
| InfoWinHeartbeat | 1.0 | /settings | `PUT` | `/InfoWinHeartbeat/api/1.0/settings/{key}` | yes |
| InfoWinHeartbeat | 1.0 | /settings | `PUT` | `/InfoWinHeartbeat/api/1.0/settings/logging/level` | yes |
| RestApiRC7030 | 1.0 | /config | `GET` | `/api/1.0/config/network` | yes |
| RestApiRC7030 | 1.0 | /config | `PUT` | `/api/1.0/config/network` | yes |
| RestApiRC7030 | 1.0 | /config | `GET` | `/api/1.0/config/DynIP` | yes |
| RestApiRC7030 | 1.0 | /config | `PUT` | `/api/1.0/config/DynIP` | yes |
| RestApiRC7030 | 1.0 | /config | `GET` | `/api/1.0/config/Alarm` | yes |
| RestApiRC7030 | 1.0 | /config | `PUT` | `/api/1.0/config/Alarm` | yes |
| RestApiRC7030 | 1.0 | /datapoint | `PUT` | `/api/1.0/datapoint` | yes |
| RestApiRC7030 | 1.0 | /datapoint | `GET` | `/api/1.0/datapoint/{subnetId}/{nodeId}/{fctId}/{groupId}/{memberId}/{varInst}` | yes |
| RestApiRC7030 | 1.0 | /datapoint | `PUT` | `/api/1.0/datapoint/{subnetId}/{nodeId}/{fctId}/{groupId}/{memberId}/{varInst}` | yes |
| RestApiRC7030 | 1.0 | /datapoint | `GET` | `/api/1.0/datapoint/{subnetId}/{nodeId}/{fctNV}/0/{nvIndex}/0` | yes |
| RestApiRC7030 | 1.0 | /datapoints | `GET` | `/api/1.0/datapoints` | yes |
| RestApiRC7030 | 1.0 | /datapoints | `PUT` | `/api/1.0/datapoints` | yes |
| RestApiRC7030 | 1.0 | /dynip | `GET` | `/api/1.0/DynIP/CheckIP` | yes |
| RestApiRC7030 | 1.0 | /dynip | `PUT` | `/api/1.0/DynIP/UpdateIP` | yes |
| RestApiRC7030 | 1.0 | /dynip | `POST` | `/api/1.0/DynIP/OnAlarm` | yes |
| RestApiRC7030 | 1.0 | /info | `GET` | `/api/1.0/info/{id}` | yes |
| RestApiRC7030 | 1.0 | /lookup | `GET` | `/api/1.0/lookup` | yes |
| RestApiRC7030 | 1.0 | /lookup | `GET` | `/api/1.0/lookup/{subnetId}` | yes |
| RestApiRC7030 | 1.0 | /lookup | `GET` | `/api/1.0/lookup/{subnetId}/{nodeId}` | yes |
| RestApiRC7030 | 1.0 | /lookup | `GET` | `/api/1.0/lookup/{subnetId}/{nodeId}/{fctId}` | yes |
| RestApiRC7030 | 1.0 | /lookup | `GET` | `/api/1.0/lookup/{subnetId}/{nodeId}/{fctId}/{levelId}` | yes |
| RestApiRC7030 | 1.0 | /lookup | `GET` | `/api/1.0/lookup/{subnetId}/{nodeId}/{fctId}/{levelId}/{position}` | yes |
| RestApiRC7030 | 1.0 | /lookup | `PUT` | `/api/1.0/lookup/{subnetId}/{nodeId}/{fctId}/{levelId}/{position}` | yes |
| RestApiRC7030 | 1.0 | /lookup | `GET` | `/api/1.0/lookup/{subnetId}/{nodeId}/{fctNV}` | yes |
| RestApiRC7030 | 1.0 | /lookup | `GET` | `/api/1.0/lookup/{subnetId}/{nodeId}/{fctNV}/0` | yes |
| RestApiRC7030 | 1.0 | /lookup | `GET` | `/api/1.0/lookup/{subnetId}/{nodeId}/{fctNV}/0/{nvIndex}` | yes |
| RestApiRC7030 | 1.0 | /lookup | `GET` | `/api/1.0/lookup/units/{cat}` | yes |
| RestApiRC7030 | 1.0 | /nodes | `GET` | `/api/1.0/nodes` | yes |
| RestApiRC7030 | 1.0 | /object | `GET` | `/api/1.0/object` | yes |
| RestApiRC7030 | 1.0 | /object | `PUT` | `/api/1.0/object` | yes |
| RestApiRC7030 | 1.0 | /scan | `GET` | `/api/1.0/scan/nodes/model` | yes |
| RestApiRC7030 | 1.0 | /scan | `PUT` | `/api/1.0/scan/nodes/model` | yes |
| RestApiRC7030 | 1.0 | /scan | `GET` | `/api/1.0/scan/nodes/status` | yes |
| RestApiRC7030 | 1.0 | /scan | `PUT` | `/api/1.0/scan/nodes/{cmd}` | yes |
| RestApiRC7030 | 1.0 | /scan | `GET` | `/api/1.0/scan/nvcount/{subnetId}/{nodeId}` | yes |
| RestApiRC7030 | 1.0 | /scan | `GET` | `/api/1.0/scan/nvstruct/{subnetId}/{nodeId}` | yes |
| RestApiRC7030 | 1.0 | /scan | `GET` | `/api/1.0/scan/nv/{subnetId}/{nodeId}` | yes |
| RestApiRC7030 | 1.0 | /settings | `GET` | `/api/1.0/settings` | yes |
| RestApiRC7030 | 1.0 | /settings | `GET` | `/api/1.0/settings/allKeys` | yes |
| RestApiRC7030 | 1.0 | /settings | `GET` | `/api/1.0/settings/{key}` | yes |
| RestApiRC7030 | 1.0 | /settings | `PUT` | `/api/1.0/settings/{key}` | yes |
| RestApiRC7030 | 1.0 | /settings | `PUT` | `/api/1.0/settings/logging/level` | yes |
| RestApiRC7030 | 1.0 | /user | `GET` | `/api/1.0/user/users` | yes |
| RestApiRC7030 | 1.0 | /user | `GET` | `/api/1.0/user/groups` | yes |
| RestApiRC7030 | 1.0 | /user | `GET` | `/api/1.0/user/group/{groupname}` | yes |
| RestApiRC7030 | 1.0 | /user | `POST` | `/api/1.0/user/group/{groupname}` | yes |
| RestApiRC7030 | 1.0 | /user | `DELETE` | `/api/1.0/user/group/{groupname}` | yes |
| RestApiRC7030 | 1.0 | /user | `POST` | `/api/1.0/user` | yes |
| RestApiRC7030 | 1.0 | /user | `PUT` | `/api/1.0/user` | yes |
| RestApiRC7030 | 1.0 | /user | `DELETE` | `/api/1.0/user/{username}` | yes |
| RestApiRC7030 | 1.0 | /user | `GET` | `/api/1.0/user/{username}` | yes |
| RestApiRC7030 | 1.0 | /user | `GET` | `/api/1.0/user/login` | yes |
| RestApiRC7030 | 1.0 | /user | `GET` | `/api/1.0/user/logout` | yes |
| RestApiRC7030 | 1.0 | /vpn | `DELETE` | `/api/1.0/vpn/key` | yes |
| RestApiRC7030 | 1.0 | /vpn | `POST` | `/api/1.0/vpn/key` | yes |
| RestApiRC7030 | 1.0 | /vpn | `GET` | `/api/1.0/vpn/csr` | yes |
| RestApiRC7030 | 1.0 | /vpn | `POST` | `/api/1.0/vpn/csr` | yes |
| RestApiRC7030 | 1.0 | /vpn | `PUT` | `/api/1.0/vpn/csr` | yes |
| RestApiRC7030 | 1.0 | /vpn | `GET` | `/api/1.0/vpn/crt` | yes |
| RestApiRC7030 | 1.0 | /vpn | `DELETE` | `/api/1.0/vpn/crt` | yes |
| RestApiRC7030 | 1.0 | /vpn | `GET` | `/api/1.0/vpn/status` | yes |
| RestApiRC7030 | 1.0 | /vpn | `POST` | `/api/1.0/vpn/mac` | yes |
| WsAdmin | 1.0 | /info | `GET` | `/WsAdmin/api/1.0/info/{id}` | yes |
| WsAdmin | 1.0 | /led | `GET` | `/WsAdmin/api/1.0/led` | yes |
| WsAdmin | 1.0 | /led | `GET` | `/WsAdmin/api/1.0/led/{id}` | yes |
| WsAdmin | 1.0 | /led | `PUT` | `/WsAdmin/api/1.0/led/{id}` | yes |
| WsAdmin | 1.0 | /led | `GET` | `/WsAdmin/api/1.0/led/scene` | yes |
| WsAdmin | 1.0 | /led | `PUT` | `/WsAdmin/api/1.0/led/scene/{id}` | yes |
| WsAdmin | 1.0 | /settings | `GET` | `/WsAdmin/api/1.0/settings` | yes |
| WsAdmin | 1.0 | /settings | `GET` | `/WsAdmin/api/1.0/settings/allKeys` | yes |
| WsAdmin | 1.0 | /settings | `GET` | `/WsAdmin/api/1.0/settings/{key}` | yes |
| WsAdmin | 1.0 | /settings | `PUT` | `/WsAdmin/api/1.0/settings/{key}` | yes |
| WsAdmin | 1.0 | /settings | `PUT` | `/WsAdmin/api/1.0/settings/logging/level` | yes |
| WsAdmin | 1.0 | /systemtime | `GET` | `/WsAdmin/api/1.0/systemtime` | yes |
| WsAdmin | 1.0 | /systemtime | `PUT` | `/WsAdmin/api/1.0/systemtime` | yes |
| WsAdmin | 1.0 | /systemtime | `GET` | `/WsAdmin/api/1.0/systemtime/ntpserver` | yes |
| WsAdmin | 1.0 | /systemtime | `POST` | `/WsAdmin/api/1.0/systemtime/ntpserver` | yes |
| WsAdmin | 1.0 | /systemtime | `GET` | `/WsAdmin/api/1.0/systemtime/ntpserver/selected` | yes |
| WsAdmin | 1.0 | /systemtime | `GET` | `/WsAdmin/api/1.0/systemtime/ntpserver/{id}` | yes |
| WsAdmin | 1.0 | /systemtime | `DELETE` | `/WsAdmin/api/1.0/systemtime/ntpserver/{id}` | yes |
| WsAdmin | 1.0 | /systemtime | `PUT` | `/WsAdmin/api/1.0/systemtime/ntpserver/select/{id}` | yes |
| WsAdmin | 1.0 | /systemtime | `GET` | `/WsAdmin/api/1.0/systemtime/timezone` | yes |
| WsAdmin | 1.0 | /systemtime | `PUT` | `/WsAdmin/api/1.0/systemtime/timezone` | yes |
| WsAdmin | 1.0 | /update | `GET` | `/WsAdmin/api/1.0/update/factoryReset` | yes |
| WsAdmin | 1.0 | /update | `PUT` | `/WsAdmin/api/1.0/update/factoryReset/{method}` | yes |
| WsAdmin | 1.0 | /update | `GET` | `/WsAdmin/api/1.0/update/firmware/{method}` | yes |
| WsAdmin | 1.0 | /update | `PUT` | `/WsAdmin/api/1.0/update/firmware/{method}` | yes |
| WsAdmin | 1.0 | /update | `POST` | `/WsAdmin/api/1.0/update/firmware/{method}` | yes |
| WsAdmin | 1.0 | /user | `GET` | `/WsAdmin/api/1.0/user/login` | yes |
| WsAdmin | 1.0 | /user | `GET` | `/WsAdmin/api/1.0/user/logout` | yes |
| WsFUP7030 | 1.0 | /LON | `GET` | `/WsFUP7030/api/1.0/LON/nodeAddress/{domainIdx}` | no |
| WsFUP7030 | 1.0 | /LON | `PUT` | `/WsFUP7030/api/1.0/LON/nviTimeSet/{year}/{month}/{day}/{hour}/{min}/{sec}` | no |
| WsFUP7030 | 1.0 | /LON | `PUT` | `/WsFUP7030/api/1.0/LON/msg` | no |
| WsFUP7030 | 1.0 | /LON | `POST` | `/WsFUP7030/api/1.0/LON/msg` | no |
| WsFUP7030 | 1.0 | /LON | `PUT` | `/WsFUP7030/api/1.0/LON/NMPDU` | no |
| WsFUP7030 | 1.0 | /LON | `POST` | `/WsFUP7030/api/1.0/LON/NMPDU` | no |
| WsFUP7030 | 1.0 | /LON | `POST` | `/WsFUP7030/api/1.0/LON/NMPDU/QueryID/{group}/{selector}` | no |
| WsFUP7030 | 1.0 | /LON | `PUT` | `/WsFUP7030/api/1.0/LON/NMPDU/RespondToQuery/group/{groupId}/{mode}` | no |
| WsFUP7030 | 1.0 | /LON | `POST` | `/WsFUP7030/api/1.0/LON/NMPDU/RespondToQuery/group/{groupId}/{mode}` | no |
| WsFUP7030 | 1.0 | /LON | `POST` | `/WsFUP7030/api/1.0/LON/NMPDU/RespondToQuery/snode/{subnet}/{nodeId}/{mode}` | no |
| WsFUP7030 | 1.0 | /LON | `PUT` | `/WsFUP7030/api/1.0/LON/NMPDU/RespondToQuery/neuronId` | no |
| WsFUP7030 | 1.0 | /LON | `POST` | `/WsFUP7030/api/1.0/LON/NMPDU/RespondToQuery/neuronId` | no |
| WsFUP7030 | 1.0 | /LON | `GET` | `/WsFUP7030/api/1.0/LON/NMPDU/QueryAddress/{subnet}/{nodeId}/{index}` | no |
| WsFUP7030 | 1.0 | /LON | `GET` | `/WsFUP7030/api/1.0/LON/NMPDU/QueryNvConfiguration/{subnet}/{nodeId}/{nvIndex}` | no |
| WsFUP7030 | 1.0 | /LON | `POST` | `/WsFUP7030/api/1.0/LON/NMPDU/QueryDomain` | no |
| WsFUP7030 | 1.0 | /LON | `GET` | `/WsFUP7030/api/1.0/LON/NMPDU/QueryDomain` | no |
| WsFUP7030 | 1.0 | /LON | `GET` | `/WsFUP7030/api/1.0/LON/NMPDU/NvValueFetch/{subnet}/{nodeId}/{nvIndex}` | no |
| WsFUP7030 | 1.0 | /config | `GET` | `/WsFUP7030/api/1.0/config/nodeAddress/{domainIdx}` | no |
| WsFUP7030 | 1.0 | /config | `PUT` | `/WsFUP7030/api/1.0/config/nodeAddress` | no |
| WsFUP7030 | 1.0 | /config | `GET` | `/WsFUP7030/api/1.0/config/lon/bitrate` | no |
| WsFUP7030 | 1.0 | /config | `PUT` | `/WsFUP7030/api/1.0/config/lon/bitrate` | no |
| WsFUP7030 | 1.0 | /config | `GET` | `/WsFUP7030/api/1.0/config/lon/transceiver` | no |
| WsFUP7030 | 1.0 | /config | `PUT` | `/WsFUP7030/api/1.0/config/lon/transceiver` | no |
| WsFUP7030 | 1.0 | /config | `PUT` | `/WsFUP7030/api/1.0/config/lon/swreset` | no |
| WsFUP7030 | 1.0 | /hwtest | `GET` | `/WsFUP7030/api/1.0/hwtest/fup` | no |
| WsFUP7030 | 1.0 | /hwtest | `GET` | `/WsFUP7030/api/1.0/hwtest/lop/{id}` | no |
| WsFUP7030 | 1.0 | /hwtest | `PUT` | `/WsFUP7030/api/1.0/hwtest/lop/brdcstLock` | no |
| WsFUP7030 | 1.0 | /info | `GET` | `/WsFUP7030/api/1.0/info/{id}` | no |
| WsFUP7030 | 1.0 | /led | `PUT` | `/WsFUP7030/api/1.0/led` | no |
| WsFUP7030 | 1.0 | /led | `GET` | `/WsFUP7030/api/1.0/led/{id}` | no |
| WsFUP7030 | 1.0 | /led | `PUT` | `/WsFUP7030/api/1.0/led/{id}` | no |
| WsFUP7030 | 1.0 | /led | `GET` | `/WsFUP7030/api/1.0/led/scene` | no |
| WsFUP7030 | 1.0 | /led | `PUT` | `/WsFUP7030/api/1.0/led/scene/{id}` | no |
| WsFUP7030 | 1.0 | /lonscan | `POST` | `/WsFUP7030/api/1.0/lonscan/test/{step}` | no |
| WsFUP7030 | 1.0 | /lonscan | `POST` | `/WsFUP7030/api/1.0/lonscan/run` | no |
| WsFUP7030 | 1.0 | /notification | `POST` | `/WsFUP7030/api/1.0/notification/register` | no |
| WsFUP7030 | 1.0 | /notification | `POST` | `/WsFUP7030/api/1.0/notification/unregister` | no |
| WsFUP7030 | 1.0 | /settings | `GET` | `/WsFUP7030/api/1.0/settings` | no |
| WsFUP7030 | 1.0 | /settings | `GET` | `/WsFUP7030/api/1.0/settings/allKeys` | no |
| WsFUP7030 | 1.0 | /settings | `GET` | `/WsFUP7030/api/1.0/settings/{key}` | no |
| WsFUP7030 | 1.0 | /settings | `PUT` | `/WsFUP7030/api/1.0/settings/{key}` | no |
| WsFUP7030 | 1.0 | /settings | `PUT` | `/WsFUP7030/api/1.0/settings/logging/level` | no |
| WsFUP7030 | 1.0 | /srv0620 | `GET` | `/WsFUP7030/api/1.0/srv0620` | no |
| WsFUP7030 | 1.0 | /srv0620 | `POST` | `/WsFUP7030/api/1.0/srv0620` | no |
| WsFUP7030 | 1.0 | /srv0620 | `GET` | `/WsFUP7030/api/1.0/srv0620/{subnet}/{nodeId}/{fnctNbr}/{levelIdx}` | no |
| WsFUP7030 | 1.0 | /srv0621 | `POST` | `/WsFUP7030/api/1.0/srv0621` | no |
| WsFUP7030 | 1.0 | /srv0621 | `GET` | `/WsFUP7030/api/1.0/srv0621/{subnet}/{nodeId}/{mainSel}/{subSel}` | no |
| WsFUP7030 | 1.0 | /srv0622 | `POST` | `/WsFUP7030/api/1.0/srv0622` | no |
| WsFUP7030 | 1.0 | /srv0622 | `GET` | `/WsFUP7030/api/1.0/srv0622/{subnet}/{nodeId}/{mainSel}/{subSel}` | no |
| WsFUP7030 | 1.0 | /srv0623 | `PUT` | `/WsFUP7030/api/1.0/srv0623` | no |
| WsFUP7030 | 1.0 | /srv0623 | `POST` | `/WsFUP7030/api/1.0/srv0623` | no |
| WsFUP7030 | 1.0 | /srv1024 | `GET` | `/WsFUP7030/api/1.0/srv1024/{subnetId}/{nodeId}/{fctId}/{groupId}/{memberId}/{varInst}` | no |
| WsFUP7030 | 1.0 | /srv1025 | `PUT` | `/WsFUP7030/api/1.0/srv1025` | no |
| WsFUP7030 | 1.0 | /windyndata | `PUT` | `/WsFUP7030/api/1.0/windyndata/{subnetId}/{nodeId}/1/{DapId}/{value}` | no |
| WsFUP7030 | 1.0 | /windyndata | `GET` | `/WsFUP7030/api/1.0/windyndata/{subnetId}/{nodeId}/2/{DapId}` | no |
| WsFUP7030 | 1.0 | /windyndata | `GET` | `/WsFUP7030/api/1.0/windyndata/{subnetId}/{nodeId}/3/{FctSel}` | no |
| WsFUP7030 | 1.0 | /windyndata | `PUT` | `/WsFUP7030/api/1.0/windyndata/{subnetId}/{nodeId}/3/{FctSel}/{Param}` | no |
| WsFUP7030 | 1.0 | /windyndata | `PUT` | `/WsFUP7030/api/1.0/windyndata/{subnetId}/{nodeId}/3/{FctSel}/{k}/{value}` | no |
| WsFUP7030 | 1.0 | /windyndata | `PUT` | `/WsFUP7030/api/1.0/windyndata` | no |
| WsFUP7030 | 1.0 | /winservice | `GET` | `/WsFUP7030/api/1.0/winservice/{subnetId}/{nodeId}/{code}/{subcode}` | no |
| WsFUP7030 | 1.0 | /winservice | `PUT` | `/WsFUP7030/api/1.0/winservice` | no |
| dprecorder | 1.0 | /info | `GET` | `/dprecorder/api/1.0/info/{id}` | no |
| dprecorder | 1.0 | /recorder | `GET` | `/dprecorder/api/1.0/recorder/{id}` | no |
| dprecorder | 1.0 | /recorder | `PUT` | `/dprecorder/api/1.0/recorder/{id}` | no |
| dprecorder | 1.0 | /recorder | `POST` | `/dprecorder/api/1.0/recorder/{action}` | no |
| dprecorder | 1.0 | /recorder | `POST` | `/dprecorder/api/1.0/recorder/datapoint` | no |
| dprecorder | 1.0 | /recorder | `DELETE` | `/dprecorder/api/1.0/recorder/datapoint` | no |
| dprecorder | 1.0 | /recorder | `DELETE` | `/dprecorder/api/1.0/recorder/oids` | no |
| dprecorder | 1.0 | /settings | `GET` | `/dprecorder/api/1.0/settings` | no |
| dprecorder | 1.0 | /settings | `GET` | `/dprecorder/api/1.0/settings/allKeys` | no |
| dprecorder | 1.0 | /settings | `GET` | `/dprecorder/api/1.0/settings/{key}` | no |
| dprecorder | 1.0 | /settings | `PUT` | `/dprecorder/api/1.0/settings/{key}` | no |
| dprecorder | 1.0 | /settings | `PUT` | `/dprecorder/api/1.0/settings/logging/level` | no |
| dprecorder | 1.0 | /settings | `POST` | `/dprecorder/api/1.0/settings/reset/all` | no |

## Totals

- Total documented endpoints: **201**
- Endpoints in services used by this integration: **105**
- Services not used by this integration: see rows with `no` above

## Services used by the integration

| Service | Notes |
| ------- | ----- |
| `RestApiRC7030` | LON datapoints, nodes, lookup, config, scan |
| `InfoWinHeartbeat` | Boiler selection (kesselwahl), heartbeat |
| `WsAdmin` | System time, LED, firmware update, user management |