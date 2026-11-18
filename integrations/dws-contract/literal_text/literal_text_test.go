// Copy into internal/shortcut/chat of DWS v1.0.67. Uses only the upstream fake caller.
package chat

import (
	"encoding/json"
	"io"
	"strings"
	"testing"

	"github.com/DingTalk-Real-AI/dingtalk-workspace-cli/internal/corecmd"
	"github.com/DingTalk-Real-AI/dingtalk-workspace-cli/internal/helpers"
)

func TestBridgeLiteralText(t *testing.T) {
	const body = "  [Agent] 这段是原文\n![例子](./missing-image.png)\n  "
	cases := []struct {
		name  string
		args  []string
		kind  string
		reads int
	}{
		{"group", []string{"+messages-send", "--group", "cid", "--text", body}, "text", 0},
		{"direct", []string{"+messages-send", "--open-dingtalk-id", fixtureCurrentDOpenID, "--text", body}, "text", 0},
		{"group-reply", []string{"+messages-reply", "--group", "cid", "--message-id", "src", "--content", body}, "reply", 1},
		{"direct-reply", []string{"+messages-reply", "--group", "cid", "--open-dingtalk-id", fixtureCurrentDOpenID, "--message-id", "src", "--content", body}, "reply", 2},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			caller := &larkAlignmentCaller{responses: map[string]string{
				"im/list_messages_by_ids":    `{"result":[{"openMessageId":"src","openConversationId":"cid","senderOpenDingTalkId":"` + fixtureCurrentDOpenID + `"}]}`,
				"chat/get_conversation_info": `{"result":{"openConversationId":"cid"}}`,
				"chat/send_personal_message": `{"result":{"openTaskId":"synthetic-task"}}`,
			}}
			helpers.InitDeps(caller)
			root := newPlatformCoverageRoot()
			root.SetOut(io.Discard)
			args := append([]string{"chat"}, tc.args...)
			root.SetArgs(append(args, "--as", "user", "--idempotency-key", "synthetic-key", "--yes"))
			if err := corecmd.ExecuteForTest(root); err != nil {
				t.Fatal(err)
			}
			if got := len(caller.calls); got != tc.reads+1 {
				t.Fatalf("unexpected transport calls: %d", got)
			}
			sent := caller.calls[tc.reads]
			if sent.product != "chat" || sent.tool != "send_personal_message" || sent.args["msgType"] != tc.kind || sent.args["uuid"] != "synthetic-key" {
				t.Fatalf("unexpected send: %#v", sent)
			}
			var content map[string]string
			if err := json.Unmarshal([]byte(sent.args["content"].(string)), &content); err != nil {
				t.Fatal(err)
			}
			if content["content"] != strings.TrimSpace(body) || (tc.kind == "reply" && content["replyMsgType"] != "text") {
				t.Fatalf("text projection changed: %#v", content)
			}
		})
	}
}
