# DingTalk Bridge channel for OpenClaw

This channel delivers messages and verified file originals between DingTalk and an existing OpenClaw agent. The bridge handles ordinary-account transport through DWS, per-chat routing and delivery receipts. OpenClaw owns the agent, its workspace, tool permissions and tool calls. A request to check a code review, search a company handbook or prepare a report follows the same message and file path.

## Install

See the [existing-host pilot](../../docs/resident-openclaw-pilot.md) when the profile already serves another channel. Use the intended profile explicitly for installation and enablement. Review the current SDK, active bindings, and execution owner first.

Use a checkout containing this plugin and the matching Python sidecar. Install the Python package in a dedicated environment, then configure and install the channel in the OpenClaw instance that should own the conversations.

```sh
python3 -m venv /absolute/path/to/bridge-venv
/absolute/path/to/bridge-venv/bin/python -m pip install /absolute/path/to/dingtalk-agent-bridge
openclaw --profile PROFILE plugins install /absolute/path/to/dingtalk-agent-bridge/integrations/openclaw-channel --accept-capabilities
openclaw --profile PROFILE plugins enable dingtalk-bridge
```

For an unattended install on OpenClaw 2026.11.3, review the local source and its declared capabilities before using these acceptance flags. When the host uses a plugin allowlist, include `dingtalk-bridge` in it. The July 2026.7.1-2 CLI uses the same local-source install command without the November-only `--accept-capabilities` option. Follow the prompts provided by that version. Replace `PROFILE` with the intended host profile. This source checkout does not require an npm registry publication.

## Verify the loaded channel

For a pinned deployment, set `plugins.entries.dingtalk-bridge.config.expectedRelease` to the package version you installed, such as `"0.2.5"`. On account startup the gateway logs the loaded release, the cancellation protocol and whether it checked the pin. Verify the route owner and a receipt separately. An incompatible release stops before starting a sidecar. Configure the pin only after installing the matching manifest.

This plugin ships from reviewed local source. OpenClaw 2026.7.1-2 can look up a registry package on cold startup when a local plugin advertises a downloadable channel without an install record. Version 0.2.2 declares its runtime channels in `openclaw.plugin.json` and omits the download catalog entry.

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

For a handover to a different durable host, set `accounts.<alias>.consumerInstance` to a stable name such as `org-pilot`. Each name has its own persisted inbox and initial handover cursor. The default name preserves the original consumer. All names for the same physical route share one execution lock. Changing the name requires a new cursor review.

### Use an existing organization workspace

The pilot covers workspace identity, historical recall, skill-based decisions, and file delivery in the originating chat. Available tools depend on the host and channel. [User workflows and observed limits](../../docs/agent-im-workflows.md)

Append a route binding to the host's existing bindings. Replace the example agent ID and account alias with the intended pair.

```json
{
  "type": "route",
  "agentId": "org-team",
  "match": { "channel": "dingtalk-bridge", "accountId": "personal" },
  "session": { "dmScope": "per-account-channel-peer" }
}
```

The selected agent provides its instructions, model, tools and workspace. Group and direct chats have separate transcripts and reply addresses. Everyone admitted to that organization agent can potentially access its workspace files. Select authorized senders accordingly. Keep each DingTalk conversation in its own session. The adapter checks the resolved key before taking ownership. An account binding works without deriving a peer identifier. The real-SDK routing checks are available in `test-contracts/shared-host.test.mjs` when OpenClaw is installed as a peer.

### Group participation

Set `groupReplyMode` on an individual group route. The sender allowlist, self-message filter and conversation binding apply in every mode.

| Mode | Who can start a turn |
|---|---|
| `command` (default) | An allowed sender beginning a message with `/agent`. |
| `mention` | An allowed sender whose message ID appears in the ordinary account’s official, group-scoped DWS mention list. A typed display name or a bare `/agent` cannot stand in for that receipt. The same-sender cancel command remains available. |
| `always` | Every eligible incoming message from an allowed sender, including a message with an original attachment. |
| `agent-decides` | The organization model chooses whether a contribution is appropriate. An explicit `/agent` starts a normal turn immediately. |

For example, set `"groupReplyMode": "agent-decides"` and `"groupReplyPrompt": "当同事明确求助、追问你或需要纠正关键事实时回答。闲聊、同事间的安排和已解答的问题保持安静。"`. The preference is scoped to this group. The decision call has zero tools. It sees bounded text, attachment names and types, and up to eight recent allowed or self messages from this group. It has no access to attachment bytes during this decision. An affirmative decision runs the usual organization agent with the verified originals and its authorized tools. An explicit negative decision is silent on DingTalk and stored with the original message ID. Model errors and malformed decisions stay pending for a bounded-backoff retry of the decision step. A restart before business dispatch resumes the side-effect-free decision. Once the organization task could have started, recovery records an uncertain result for review. Later ordinary messages from that sender wait behind the pending decision, including across a restart. Other allowlisted senders can proceed. The separate stop path continues to service a running task.

Mention mode uses pinned DWS `chat message list-mentions` through the existing bridge-wide process and credential circuit. It scopes queries to the current account, group and one-minute time window, and reuses the result for already ingested messages. A missing result on a fresh message, an incomplete index page without a positive match, or a failed lookup defers that message. This follows DWS indexing, including its treatment of group-wide mentions; there is no native @ notification guarantee beyond the supplied index. The sidecar's `summary` with `includeInbox: true` reports pending decisions and explicit silent completions. Hold ownership while any participation decisions are pending. If a business turn produces no final reply while an outbound tool or a separate scheduled send was active, its outcome stays unknown for reconciliation. Later inbox messages can still run.

## Use the channel

- Private chat accepts an allowlisted sender’s text and original files directly. By default group chat dispatches messages beginning with `/agent`. Plain group messages stay in the bridge inbox.
- To hand off files in a group, send the originals and then send `/agent --files ["report.csv","notes.txt"] Summarize the report`. Use 1–8 exact, distinct names. Each file must have a unique match from you among the preceding 50 group messages within 30 minutes. Files sent before the channel's initial cursor are eligible for selection. Only the new command starts a turn. A native reply on your own file also works when DingTalk includes its sender and original resource. If the client omits that information, use the filename command. A single message containing both a command and attachments also works.
- The host receives verified originals in its own inbound media store. Host text keeps its wording and formatting. A reply line that exposes a local attachment path or inbound media identifier is replaced with a privacy notice. To return an artifact, use the normal OpenClaw local-media reply with a file the current session can read. OpenClaw checks the session access and stages a copy in its outbound media store. The plugin reads that copy and restores the original filename. Text decorations such as a bot name belong to the host. Long text is split losslessly at the 5120 UTF-16-unit limit. Literal Markdown image syntax is plain text on the pinned DWS ordinary-account text and quoted-reply commands. DWS trims outer whitespace on each physical message. Send a file when the recipient needs the exact bytes.
- DingTalk may append `(1)` or another numeric suffix when an output name already exists. For an exact name, choose one unused in the conversation/cloud drive. Verify client Save As bytes, SHA-256 and filename; a separate graphical editor is not required.
- Use `/agent cancel` (or `/stop` in a direct conversation) to cancel your current turn. Once dispatch has stopped, a matching cancellation with no send attempt or uncertain I/O is recorded as `canceled`; it is terminal and will not replay. Submitted sends, uncertain I/O and interrupted hosts retain `unknown` and require review using the original key. Cancellation fences later sends; it does not undo local tool effects that already occurred.
- A restart retains consumed-message and send keys. Interrupted or ambiguous dispatches remain visible to the operator through the sidecar ledger. The plugin does not automatically execute an uncertain turn again. Proactive sends require an active configured target and a durable ID supplied by OpenClaw for that individual intent. In 2026.11.3 a queued batch with several independent payloads may lack such an ID and will be rejected. Individual messages can also be sent through the bridge CLI with an explicit key.

### Hand off a photo and a separate document together

Send the photo and the file in the same conversation from the same DingTalk account. Then send:

```text
/agent --attachments [{"image":1},"交接单.txt"] 对照照片检查交接单，再把结果发回来
```

This works in a group or direct conversation. Each filename selects one uniquely named file. `{"image":1}` selects your most recent top-level photo **before this instruction**, `{"image":2}` the one before it. Within one image strip, count from the right. The adapter checks up to 50 preceding conversation events and 30 minutes, preserves the requested order, and verifies every original before the task reaches the model. Another sender's photo, a quoted photo or a later upload cannot take a slot. An ambiguous filename, unresolved image position or unreadable original produces a notice for the explicit request. Use 1–8 distinct selectors. In a direct conversation the `/agent ` prefix is optional.

In an `agent-decides` group, after posting a photo you can ask “读刚才那张图上的订单号”. The channel supplies the original if you sent the only matching image in the last two minutes, that interval contains at most eight preceding events, and this consumer observed the upload. The same rule covers a recent file or document. Multiple matching images, a matching upload by another person, incomplete history or a quoted copy require a native quote or the explicit selection above. The participation decision runs before any download. Other messages retain their original boundaries.

For turns with originals, the host receives a tool-use hint for workspace-staged attachments. Filesystem tools use the staged path in the current model input. The virtual inbound media identifier can accompany that path. User-facing replies use the filename.

### When several messages arrive together

Each route has its own durable inbox, cursor and session. Eligible messages run one turn at a time in transport sequence. A burst of text, images and files keeps the original message boundaries. Media inside one message retains its order. A later text can refer to the earlier turns in the same session. In a group, the filename command above explicitly binds several originals to one task.

While preparing an original, the route continues receiving input and recognizes the current sender’s stop command. One slow download can delay ordinary turns in that conversation. Other routes keep working independently. The sidecar verifies the complete original before submitting it to the host. After three failed preparation attempts, it records the failed original, and an explicitly requested task or direct chat receives a notice if that notification can be delivered. Later messages can proceed. Host-side staging failures also receive a separate record.

The inbox cursor advances in the same transaction as its input rows. A restarted owner can safely resume pending downloads which never reached dispatch or cancellation. An interrupted host dispatch stays under its original ID for review. Inspect the private sidecar's `summary` operation with `includeInbox: true` for projection issues, inbox states and failed originals. The bridge can account for events it received; a message missing from upstream history requires separate investigation.

## Agent tools

Configure business tools and their credentials in the OpenClaw agent or its existing tool provider. Once an incoming request is admitted, OpenClaw invokes the tools available in that session and supplies the reply text or files for the channel to deliver. The host also controls network access for those calls.

For an offline example using a real, pinned OpenClaw SDK, run `python3 scripts/probe_openclaw_native_channel.py /path/to/openclaw --workspace-context` from the repository root. The probe uses the host’s workspace reader and a skill in an isolated workspace and verifies the replies in simulated DingTalk conversations.

When upgrading from 0.2.3 or 0.2.4, remove the retired `githubPullRequests` setting from each affected DingTalk account and its `dingtalk_github_pull_request` allowlist entries from the host. If that lookup is still needed, configure a suitable tool at the host. Preserve other channel bindings and agent tool permissions during the migration.

## Send proactively from the host

```sh
openclaw --profile PROFILE message send --channel dingtalk-bridge --account personal --target YOUR_CONVERSATION_ID --message "The report is ready" --json
openclaw --profile PROFILE message send --channel dingtalk-bridge --account personal --target YOUR_CONVERSATION_ID --message "Attached report" --media /absolute/path/to/report.pdf --json
```

These proactive CLI examples require a host that supplies a durable delivery ID. OpenClaw 2026.7.1-2 omits the ID for both text and media, so those commands stop before transport. Reactive replies to an incoming task work on that version. For a standalone proactive delivery, use the bridge CLI with an explicit stable key.

On the tested November host, the CLI delegates to the running Gateway. Its durable queue assigns each send an intent ID. A new command with the same text delivers a new message. On recovery the channel looks up the persisted parts of the original intent and reconciles their existing bridge keys. The host receives a successful receipt only after all physical message IDs are confirmed. An incomplete plan or ambiguous part stays unresolved. Calls that bypass the host queue or supply multiple independent payloads without an individual durable ID are refused before transport.

On the existing organization host, both an authorized DingTalk group and a direct chat completed file tasks and follow-up turns in their own sessions. Disabling and re-enabling only the DingTalk channel preserved both sessions and delivered one new message received during the gap exactly once in this sample. A full handback restored both original route owners and verified their programs, sessions and seven physical delivery receipts. In a later real group turn, the requester stopped the model after file reads began. The canceled input and its stop command have one durable link, with zero send attempts. An earlier private-chat input remains unknown and prevents a strict handback. [Live group cancellation](../../evidence/2026-11-19/openclaw-resident-live-group-cancel.json) Keep the E154 unknown send under its original key. [Resident pilot receipt](../../evidence/2026-11-19/openclaw-resident-live-pilot.json)
