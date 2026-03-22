import json
from Agents.chat_agent.tools.helpers import build_diagram_streaming

payload = '{"nodes":{"clients":{"label":"Clients (Mobile / Web)","shape":"rectangle","row":0,"col":2},"api_gateway":{"label":"API Gateway / Load Balancer","shape":"diamond","row":1,"col":2},"ws_svc":{"label":"WebSocket / Real-time Gateway","shape":"rectangle","row":2,"col":2},"conn_mgr":{"label":"Connection Manager","shape":"rectangle","row":3,"col":1},"chat_api":{"label":"Chat API / Message Processor","shape":"rectangle","row":3,"col":3},"presence_svc":{"label":"Presence Service","shape":"rectangle","row":4,"col":1},"message_broker":{"label":"Message Broker (Pub/Sub)","shape":"ellipse","row":4,"col":3},"message_store":{"label":"Message Store (Cassandra)","shape":"ellipse","row":5,"col":3},"user_db":{"label":"User / Metadata DB (Postgres)","shape":"ellipse","row":5,"col":2},"offline_queue":{"label":"Offline Queue","shape":"ellipse","row":5,"col":1},"media_store":{"label":"Media Store (S3)","shape":"ellipse","row":6,"col":3},"push_svc":{"label":"Push / Notification Service","shape":"rectangle","row":6,"col":1}},"layout":"grid","direction":"top-bottom","edges":[{"from":"clients","to":"api_gateway","label":"HTTPS / WS"},{"from":"api_gateway","to":"ws_svc","label":"Upgrade / Proxy"},{"from":"ws_svc","to":"conn_mgr","label":"connection state"},{"from":"ws_svc","to":"chat_api","label":"events / RPC"},{"from":"conn_mgr","to":"presence_svc","label":"presence updates"},{"from":"presence_svc","to":"user_db","label":"read/write"},{"from":"chat_api","to":"message_broker","label":"publish"},{"from":"message_broker","to":"ws_svc","label":"deliver (pub/sub)"},{"from":"chat_api","to":"message_store","label":"persist"},{"from":"message_broker","to":"offline_queue","label":"enqueue"},{"from":"offline_queue","to":"push_svc","label":"notify"},{"from":"chat_api","to":"media_store","label":"store attachments"},{"from":"chat_api","to":"user_db","label":"user/meta"}]}'

desc = json.loads(payload)

try:
    list(build_diagram_streaming(desc, []))
    print("SUCCESS")
except Exception as e:
    import traceback
    traceback.print_exc()
