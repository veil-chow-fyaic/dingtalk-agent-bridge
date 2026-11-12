// Copy into an isolated pinned official checkout under internal/bridgecontract.
// Only declaration-tree construction and flag parsing: NEVER Execute or RunE.
package bridgecontract

import (
    "encoding/json"
    "os"
    "strings"
    "testing"

    "github.com/DingTalk-Real-AI/dingtalk-workspace-cli/internal/app"
    "github.com/spf13/cobra"
)

type invocation struct { Name string `json:"name"`; Args []string `json:"args"` }

func TestBridgePreparedArguments(t *testing.T) {
    t.Setenv("DWS_CONFIG_DIR", t.TempDir())
    path := os.Getenv("BRIDGE_ARGUMENT_CASES")
    if path == "" { t.Fatal("BRIDGE_ARGUMENT_CASES is required") }
    data, err := os.ReadFile(path); if err != nil { t.Fatal(err) }
    var cases []invocation
    if err := json.Unmarshal(data, &cases); err != nil { t.Fatal(err) }
    if len(cases) != 8 { t.Fatalf("want two queries and six office cases, got %d", len(cases)) }
    for _, tc := range cases { t.Run(tc.Name, func(t *testing.T) {
        root := app.NewSchemaSourceRootCommand()
        cmd, args, err := root.Find(tc.Args); if err != nil { t.Fatal(err) }
        cmd.InitDefaultHelpFlag()
        if err := cmd.ParseFlags(args); err != nil { t.Fatal(err) }
        if cmd.Flags().Lookup("profile").Value.String() != "synthetic-corp:synthetic-user" { t.Fatal("profile not bound") }
        if cmd.Flags().Lookup("format").Value.String() != "json" { t.Fatal("format not bound") }
    }) }
}

func TestBridgeOfficeFlagSurface(t *testing.T) {
    t.Setenv("DWS_CONFIG_DIR", t.TempDir())
    // Walk every declared office command, including descendants. Only parse
    // globally injected flags, never execute pre-run, auth, handlers or help.
    for _, family := range []string{"doc", "todo", "calendar", "mail", "drive", "minutes"} {
        root := app.NewSchemaSourceRootCommand()
        group, _, err := root.Find([]string{family}); if err != nil || group == root { t.Fatalf("missing %s", family) }
        count, parsed, skipped := 0, 0, 0
        var visit func(*cobra.Command)
        visit = func(cmd *cobra.Command) {
            count++
            if cmd.DisableFlagParsing { skipped++ } else {
            parsed++
            cmd.InitDefaultHelpFlag()
            if err := cmd.ParseFlags([]string{"--profile", "synthetic-corp:synthetic-user", "--format", "json"}); err != nil { t.Fatalf("%s: %v", cmd.CommandPath(), err) }
            if err := cmd.ParseFlags([]string{"--as", "user"}); err == nil || !strings.Contains(err.Error(), "unknown flag: --as") { t.Fatalf("%s as contract differs: %v", cmd.CommandPath(), err) }
            }
            for _, child := range cmd.Commands() { visit(child) }
        }
        visit(group)
        t.Logf("family=%s declaredCommands=%d parsedCommands=%d navigationWithoutParser=%d", family, count, parsed, skipped)
    }
}
