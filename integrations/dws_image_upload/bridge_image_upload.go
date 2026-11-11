// Local bridge supplement for DWS v1.0.67 (Apache-2.0 upstream).
// Reuses official helpers; no credential, HTTP or media protocol implementation.
package helpers

import (
	"github.com/DingTalk-Real-AI/dingtalk-workspace-cli/internal/corecmd/contract"
	"github.com/DingTalk-Real-AI/dingtalk-workspace-cli/internal/output"
	"github.com/spf13/cobra"
)

var bridgeImageSpec = imageUploadSpec{
	BizType: "CHAT_IMAGE", MaxBytes: 2 * 1024 * 1024, Compress: false,
	MediaUsage: "发送独立聊天图片（本地 bridge 补充命令）",
	Identity: contract.ToolIdentitySpec{
		ProductID: "chat", Name: "bridge_image_upload",
		CanonicalPath: "chat.bridge_image_upload",
		CLIPath:       "chat bridge-image-upload", PrimaryCLIPath: "chat bridge-image-upload",
	},
}

func newBridgeImageUploadCommand() *cobra.Command {
	return NewLeafCommand(LeafSpec{
		Use:           "bridge-image-upload",
		Short:         "本地 bridge 补充：上传原始图片，不发送消息、不自动压缩",
		OutputRollout: output.RolloutUnifiedActive,
		Flags:         []LeafFlag{{Name: "file", Usage: imageUploadFlagUsage(bridgeImageSpec), MarkRequired: true}},
		Safety:        contract.SafetySpec{Effect: "write", Risk: "low", Confirmation: "user_required", Idempotency: "unknown"},
		Contract: LeafContract{
			Identity:    bridgeImageSpec.Identity,
			Description: "Local supplement exposing official CHAT_IMAGE upload; not an upstream DWS command",
			Selection: contract.SelectionSpec{
				AgentSummary: "Upload an original image for a later native image message",
				UseWhen:      []string{"A local bridge needs a CHAT_IMAGE mediaIdV2 before reserving a separate message send"},
				AvoidWhen:    []string{"An existing mediaId is available; use official chat +messages-send"},
				Examples:     []string{"dws chat bridge-image-upload --file ./image.png"},
			},
			DryRun: &contract.DryRunSpec{PreviewKind: "plan", RemoteReads: false},
			Result: &contract.ResultSpec{
				Outcomes:   []contract.ResultOutcome{contract.ResultOutcomeSuccess, contract.ResultOutcomeFailure},
				DataSchema: imageUploadDataSchema(bridgeImageSpec),
			},
			Interface:  &contract.InterfaceSpec{Mode: "composite", Availability: "available", Reason: "Local leaf reusing official runImageUpload with CHAT_IMAGE"},
			Parameters: []contract.ParamDecl{{Name: "file", Required: boolPtr(true)}},
		},
		Call: func(cmd *cobra.Command, tool string, args map[string]any) error {
			return runImageUpload(bridgeImageSpec, cmd)
		},
	})
}
