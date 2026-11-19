# DingTalk Bridge channel for OpenClaw

E155 passed real-model and client file acceptance in both group and direct chat. The new group task filters a product catalog by color; it is independent of the unresolved E154 shipment task. Only digests and byte counts are published in the [E155 receipt](../../docs/155-openclaw-two-route-file-acceptance.md). [PR #9](https://github.com/veil-chow-fyaic/dingtalk-agent-bridge/pull/9) shipped. The [deployment record](../../docs/156-native-channel-deployment.md) identifies the running core and the original gateway bindings.

An OpenClaw channel for existing DingTalk groups and private conversations. Your local DingTalk Agent Bridge handles ordinary-account DWS transport, attachment integrity and delivery reconciliation. OpenClaw owns the agent, prompts, session and reply content.

## Install

See the [existing-host pilot](../../docs/resident-openclaw-pilot.md) when the profile already serves another channel. Use the intended profile explicitly for installation and enablement. Review the current SDK, active bindings, and execution owner first.

Use a checkout containing this plugin and the matching Python sidecar. Install the Python package in a dedicated environment, then configure and install the channel in the OpenClaw instance that should own the conversations.

```sh
python3 -m venv /absolute/path/to/bridge-venv
/absolute/path/to/bridge-venv/bin/python -m pip install /absolute/path/to/dingtalk-agent-bridge
openclaw plugins install /absolute/path/to/dingtalk-agent-bridge/integrations/openclaw-channel --accept-capabilities
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
              "initialCursor": 12345
            }
          ]
        }
      }
    }
  }
}
```

Replace the example cursor `12345` with the actual reviewed sequence for that route. A previously used consumer resumes its persisted cursor.

For a group, add a route with `conversationType: "group"` and its permitted senders. The sidecar uses the bridge service configuration, its existing HTTP credential, and literal loopback. `bridgePort` defaults to 18768. `pollIntervalMs` defaults to 2000. Old built-in gateway routes retain their existing execution owner.

## Use the channel

- Private chat accepts an allowlisted sender’s text and original files directly. Group chat dispatches messages beginning with `/agent`. Plain group messages stay in the bridge inbox.
- To hand off files in a group, send the originals and then send `/agent --files ["report.csv","notes.txt"] Summarize the report`. Use 1–8 exact, distinct names. Each file must have a unique match from you among the preceding 50 group messages within 30 minutes. Files sent before the channel's initial cursor are eligible for selection. Only the new command starts a turn. A native reply on your own file also works when DingTalk includes its sender and original resource. If the client omits that information, use the filename command. A single message containing both a command and attachments also works.
- The host receives verified originals in its own inbound media store. Host text is forwarded unchanged. To return an artifact, use the normal OpenClaw local-media reply with a file the current session can read. OpenClaw checks the session access and stages a copy in its outbound media store. The plugin reads that copy and restores the original filename. Text decorations such as a bot name belong to the host. Long text is split losslessly at the 5120 UTF-16-unit limit. Literal Markdown image syntax is plain text on the pinned DWS ordinary-account text and quoted-reply commands. DWS trims outer whitespace on each physical message. Send a file when the recipient needs the exact bytes.
- DingTalk may append `(1)` or another numeric suffix when an output name already exists. For an exact name, choose one unused in the conversation/cloud drive. Verify client Save As bytes, SHA-256 and filename; a separate graphical editor is not required.
- Use `/agent cancel` to signal cancellation of the current turn started by the same sender. A canceled turn cannot start a later send. A send or tool action that already began can still take effect.
- A restart retains consumed-message and send keys. Interrupted or ambiguous dispatches remain visible to the operator through the sidecar ledger. The plugin does not automatically execute an uncertain turn again. Proactive sends require an active configured target and a durable ID supplied by OpenClaw for that individual intent. In 2026.11.3 a queued batch with several independent payloads may lack such an ID and will be rejected. Individual messages can also be sent through the bridge CLI with an explicit key.

## Send proactively from the host

```sh
openclaw message send --channel dingtalk-bridge --account personal --target YOUR_CONVERSATION_ID --message "The report is ready" --json
openclaw message send --channel dingtalk-bridge --account personal --target YOUR_CONVERSATION_ID --message "Attached report" --media /absolute/path/to/report.pdf --json
```

The CLI delegates to the running Gateway. Its durable queue assigns each send an intent ID. A new command with the same text delivers a new message. On recovery the channel looks up the persisted parts of the original intent and reconciles their existing bridge keys. The host receives a successful receipt only after all physical message IDs are confirmed. An incomplete plan or ambiguous part stays unresolved. Calls that bypass the host queue or supply multiple independent payloads without an individual durable ID are refused before transport.

SDK/lifecycle tests retain their synthetic scope. E155 adds accepted real group/direct file samples; it does not resolve the old E154 unknown send. Never retry an unknown intent under a new key. See [E155](../../docs/155-openclaw-two-route-file-acceptance.md) and [PR #9](https://github.com/veil-chow-fyaic/dingtalk-agent-bridge/pull/9) for the precise acceptance and publication boundaries.
