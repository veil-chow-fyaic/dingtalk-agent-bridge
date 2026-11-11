package helpers

import (
	"bytes"
	"context"
	"encoding/base64"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"

	"github.com/DingTalk-Real-AI/dingtalk-workspace-cli/internal/corecmd"
	"github.com/DingTalk-Real-AI/dingtalk-workspace-cli/internal/output"
	"github.com/DingTalk-Real-AI/dingtalk-workspace-cli/internal/testseam"
	"github.com/spf13/cobra"
)

func TestCrossPlatformCoverageBridgeImage(t *testing.T) {
	for _, tc := range []struct {
		name, content, response string
		dry, fail               bool
		calls                   int
	}{
		{"success", "\x89PNG\r\n\x1a\nfixture", `{"success":true,"mediaIdV2":"$image"}`, false, false, 1},
		{"dry", "\x89PNG\r\n\x1a\nfixture", "", true, false, 0},
		{"invalid", "not an image", "", false, true, 0},
		{"oversized", "\x89PNG\r\n\x1a\n" + string(bytes.Repeat([]byte{'x'}, 2*1024*1024)), "", false, true, 0},
		{"server-failure", "\x89PNG\r\n\x1a\nfixture", `{"success":false}`, false, true, 1},
		{"v1-only", "\x89PNG\r\n\x1a\nfixture", `{"success":true,"mediaIdV1":"@legacy"}`, false, true, 1},
	} {
		t.Run(tc.name, func(t *testing.T) {
			path := filepath.Join(t.TempDir(), "image.png")
			if err := os.WriteFile(path, []byte(tc.content), 0600); err != nil {
				t.Fatal(err)
			}
			caller := &scriptedToolCaller{format: "json", dry: tc.dry, steps: []scriptedToolStep{{text: tc.response}}}
			testseam.Protect(t, &deps)
			InitDeps(caller)
			var buf bytes.Buffer
			deps.Out.w = &buf
			cmd := newBridgeImageUploadCommand()
			cmd.Flags().Bool("yes", true, "confirmed test")
			cmd.Flags().Bool("dry-run", tc.dry, "preview")
			cmd.Flags().String("format", "json", "format")
			ctx, _ := output.WithResultStore(context.Background())
			cmd.SetContext(ctx)
			cmd.SetOut(&buf)
			cmd.SetErr(&buf)
			cmd.SetArgs([]string{"--file", path, "--yes"})
			cmd.PostRunE = func(executed *cobra.Command, _ []string) error {
				_, _, err := output.EmitStoredResult(executed)
				return err
			}
			err := corecmd.ExecuteForTest(cmd)
			if (err != nil) != tc.fail || caller.calls != tc.calls {
				t.Fatalf("err=%v calls=%d", err, caller.calls)
			}
			if tc.calls == 1 && (caller.server != "dingtalk-file" || caller.tool != "upload_media" || caller.args["bizType"] != "CHAT_IMAGE" || caller.args["content"] != base64.StdEncoding.EncodeToString([]byte(tc.content))) {
				t.Fatal("wrong upload or changed bytes")
			}
			if !tc.fail {
				var envelope struct {
					OK   bool           `json:"ok"`
					Data map[string]any `json:"data"`
				}
				if err := json.Unmarshal(buf.Bytes(), &envelope); err != nil {
					t.Fatal(err)
				}
				if !envelope.OK {
					t.Fatal("missing success envelope")
				}
				if !tc.dry && (envelope.Data["mediaIdV2"] != "$image" || envelope.Data["compressed"] != false) {
					t.Fatal("incorrect upload receipt")
				}
			}
		})
	}
}
