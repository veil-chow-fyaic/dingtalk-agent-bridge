# DingTalk Bridge channel for OpenClaw

An OpenClaw channel for existing DingTalk groups and private conversations. Your local DingTalk Agent Bridge handles ordinary-account DWS transport, attachment integrity and delivery reconciliation. OpenClaw owns the agent, prompts, session and reply content.

## Install

Use a checkout containing this plugin and the matching Python sidecar. Install the Python package in a dedicated environment, then configure and install the channel in the OpenClaw instance that should own the conversations.

```sh
python3 -m venv /absolute/path/to/bridge-venv
/absolute/path/to/bridge-venv/bin/python -m pip install /absolute/path/to/dingtalk-agent-bridge
openclaw plugins install /absolute/path/to/dingtalk-agent-bridge/integrations/openclaw-channel --force --accept-capabilities
openclaw plugins enable dingtalk-bridge
```

For an unattended install on OpenClaw 2026.11.3, review the local source and its declared capabilities before using these acceptance flags. When the host uses a plugin allowlist, include `dingtalk-bridge` in it. The tested SDK and CLI version is 2026.11.3. This source checkout does not require an npm registry publication.

## Select the routes

Take a service route assigned to this host by the bridge operator (`executionOwner: "openclaw"`). Set an explicit initial transport event sequence for a new consumer. Use a verified current sequence to start with new traffic. A value of zero elects to process eligible existing history, and restart uses the persisted cursor. On an existing service, use the bridge's route handover procedure before enabling an alternate execution owner.

In the OpenClaw configuration, the account alias (`personal` below) is local to the host. Set the physical bridge account and conversation IDs and the exact stable DingTalk sender IDs allowed to invoke the host.

```json
{
  "channels": {
    "dingtalk-bridge": {
      "enabled": true,
      "python": "/absolute/path/to/bridge-venv/bin/python",
      "bridgeRoot": "/absolute/path/to/running-bridge",
      "accounts": {
        "personal": {
          "bridgeAccountId": "YOUR_BRIDGE_ACCOUNT_ID",
          "routes": [
            {
              "conversationId": "YOUR_DIRECT_CONVERSATION_ID",
              "conversationType": "direct",
              "allowSenders": ["AUTHORIZED_DINGTALK_SENDER_ID"],
              "initialCursor": 0
            }
          ]
        }
      }
    }
  }
}
```

For a group, add a route with `conversationType: "group"` and its permitted senders. The sidecar uses the bridge service configuration, its existing HTTP credential, and literal loopback. `bridgePort` defaults to 18768. `pollIntervalMs` defaults to 2000. Old built-in gateway routes retain their existing execution owner.

## Use the channel

- Private chat accepts an allowlisted sender’s text and original files directly. Group chat dispatches messages beginning with `/agent`. Plain group messages stay in the bridge inbox.
- To hand off a file in a group, send the file and then use DingTalk’s native reply on your own file message with `/agent <task>`. A single message containing both the command and its attachments also works. The filename lookup command `/agent --files` belongs to the separate built-in gateway.
- The host receives verified originals in its own inbound media store. Host text is forwarded unchanged. To return an artifact, use the normal OpenClaw local-media reply with a file the current session can read. OpenClaw checks the session access and stages a copy in its outbound media store. The plugin reads that copy and restores the original filename. Text decorations such as a bot name belong to the host. Long text is split losslessly at the 5120 UTF-16-unit limit. Literal Markdown image syntax is plain text on the pinned DWS ordinary-account text and quoted-reply commands. DWS trims outer whitespace on each physical message. Send a file when the recipient needs the exact bytes.
- Use `/agent cancel` to signal cancellation of the current turn started by the same sender. A canceled turn cannot start a later send. A send or tool action that already began can still take effect.
- A restart retains consumed-message and send keys. Interrupted or ambiguous dispatches remain visible to the operator through the sidecar ledger. The plugin does not automatically execute an uncertain turn again. Proactive sends require an active configured target and a durable ID supplied by OpenClaw for that individual intent. In 2026.11.3 a queued batch with several independent payloads may lack such an ID and will be rejected. Individual messages can also be sent through the bridge CLI with an explicit key.

## Send proactively from the host

```sh
openclaw message send --channel dingtalk-bridge --account personal --target YOUR_CONVERSATION_ID --message "The report is ready" --json
openclaw message send --channel dingtalk-bridge --account personal --target YOUR_CONVERSATION_ID --message "Attached report" --media /absolute/path/to/report.pdf --json
```

The CLI delegates to the running Gateway. Its durable queue assigns each send an intent ID. A new command with the same text delivers a new message. On recovery the channel looks up the persisted parts of the original intent and reconciles their existing bridge keys. The host receives a successful receipt only after all physical message IDs are confirmed. An incomplete plan or ambiguous part stays unresolved. Calls that bypass the host queue or supply multiple independent payloads without an individual durable ID are refused before transport.

Hosted SDK loading and local tests use synthetic identities. See the project's [adapter evidence and delivery status](../../docs/architecture/agent-integration-map.md) for live verification.
