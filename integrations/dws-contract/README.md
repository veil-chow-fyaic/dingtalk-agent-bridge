# Fixed official CLI argument contract

This fixture validates bridge-generated argv against the pinned official v1.0.67 declaration tree (63a7c4906c7dee10750011ea309b9eb78abb7eb0). It does not run an installed DWS binary, command handler, pre-run/auth hook, help renderer or network request.

`export_arguments.py` emits synthetic group/direct queries using the actual checker argument builder and six office argument arrays using the actual proxy builder. It never loads local account configuration.

Copy `flags_test.go` into `internal/bridgecontract/` in a separate archive of the fixed official source. Run only that package using the existing Go toolchain, with GOPROXY=off, GOSUMDB=off, GOTOOLCHAIN=local and BRIDGE_ARGUMENT_CASES pointing at the generated synthetic JSON. Do not add this fixture to internal/app: its TestMain performs keychain cleanup, which is outside this verification's scope. Do not modify the reference checkout or execute the DWS main entrypoint.

The fixture calls `app.NewSchemaSourceRootCommand`, `Find`, `InitDefaultHelpFlag` and `ParseFlags`. The declaration-only constructor skips runtime profile selection, helper initialization and runtime extensions. No `Execute`/`RunE` is called. CLI help flag registration is necessary because direct ParseFlags otherwise returns pflag's help sentinel rather than parsing the complete argv.

Office descendants with DisableFlagParsing are navigation/error stubs; their count is reported separately, never claimed as successful flag parsing. E083 observed 529 declarations: 518 parsed commands and 11 navigation stubs. All 518 inherit profile/format and reject an injected --as. Other families such as chat sending or event can have command-specific --as; it is not a global flag.

First bad fixture results and the eight old-argv failures remain under local/official-argument-contract-20261112. Passing this parser contract does not prove authentication, RPC success or UI delivery.

Current operation and deployment status are maintained in the [runbook](../../docs/15-service-runbook.md) and [project overview](../../docs/102-user-requirements-and-roadmap.md). This fixed parser fixture is not a live authentication or UI test; do not repeat real credential diagnostics to validate it.

## Literal text on personal-account sends

Copy `literal_text/literal_text_test.go` to `internal/shortcut/chat/` in a clean archive of the pinned v1.0.67 source. Run `go test ./internal/shortcut/chat -run '^TestBridgeLiteralText$' -count=1 -v` with the offline Go settings above. This fixture uses the upstream in-memory fake caller and synthetic IDs for group and direct sends and quoted replies. It checks each resulting RPC content string, including the shortcut’s trimming of outer whitespace, an internal newline and a literal Markdown image marker referencing a nonexistent file. It exercises the bridge's actual `+messages-send --text` and `+messages-reply --content` shortcuts.
