// Copyright 2026 OpenAI
// SPDX-License-Identifier: Apache-2.0
// Executes only this test binary. No security executable, real store or login.
package keyring

import (
	"context"
	"encoding/base64"
	"errors"
	"io"
	"os"
	"os/exec"
	"strings"
	"testing"
	"time"
)

var selectedMode string
var observedCommand *exec.Cmd
var spawnRequests int

func TestMain(m *testing.M) {
	keychainCommandContext = func(ctx context.Context, program string, args ...string) *exec.Cmd {
		if program != "/usr/bin/security" {
			panic("unexpected command path")
		}
		if !(len(args) == 1 && args[0] == "-i") && !(len(args) == 5 && args[0] == "find-generic-password") {
			panic("unexpected command arguments")
		}
		spawnRequests++
		cmd := exec.CommandContext(ctx, os.Args[0], "-test.run=^TestSyntheticKeyringChild$")
		cmd.Env = append(os.Environ(), "DAB_KEYRING_CHILD="+selectedMode)
		observedCommand = cmd
		return cmd
	}
	os.Exit(m.Run())
}
func TestSyntheticKeyringChild(t *testing.T) {
	mode := os.Getenv("DAB_KEYRING_CHILD")
	if mode == "" {
		t.Skip("helper only")
	}
	switch mode {
	case "hang":
		for {
			time.Sleep(time.Hour)
		}
	case "raw":
		os.Stdout.WriteString("synthetic-value\n")
	case "base64":
		os.Stdout.WriteString(base64EncodingPrefix + base64.StdEncoding.EncodeToString([]byte("synthetic\n中文")) + "\n")
	case "hex":
		os.Stdout.WriteString(encodingPrefix + "73796e746865746963\n")
	case "notfound":
		os.Stderr.WriteString("could not be found\n")
		os.Exit(44)
	case "denied":
		os.Stderr.WriteString("synthetic-access-denied\n")
		os.Exit(51)
	case "stdin":
		data, _ := io.ReadAll(os.Stdin)
		if !strings.HasPrefix(string(data), "add-generic-password -U -s ") || !strings.Contains(string(data), base64EncodingPrefix) || !strings.HasSuffix(string(data), "\n") {
			os.Exit(17)
		}
	case "exit":
		os.Exit(8)
	default:
		os.Exit(19)
	}
	os.Exit(0)
}
func TestReadEncodingAndFailureSemantics(t *testing.T) {
	cases := []struct {
		mode, want string
		missing    bool
	}{{"raw", "synthetic-value", false}, {"base64", "synthetic\n中文", false}, {"hex", "synthetic", false}, {"notfound", "", true}, {"denied", "", false}}
	for _, tc := range cases {
		t.Run(tc.mode, func(t *testing.T) {
			selectedMode = tc.mode
			value, err := GetContext(context.Background(), "synthetic", "user")
			if value != tc.want {
				t.Fatalf("value mismatch")
			}
			if errors.Is(err, ErrNotFound) != tc.missing {
				t.Fatalf("classification %v", err)
			}
			if tc.mode == "denied" {
				var exit *exec.ExitError
				if !errors.As(err, &exit) || exit.ExitCode() != 51 {
					t.Fatal("exit status lost")
				}
				if strings.Contains(err.Error(), "synthetic-access-denied") {
					t.Fatal("stderr leaked")
				}
			} else if !tc.missing && err != nil {
				t.Fatal(err)
			}
		})
	}
}
func TestGetAndSetTimeoutReapActualOwnedChild(t *testing.T) {
	for _, op := range []string{"get", "set"} {
		t.Run(op, func(t *testing.T) {
			selectedMode = "hang"
			ctx, cancel := context.WithTimeout(context.Background(), 200*time.Millisecond)
			defer cancel()
			var err error
			if op == "get" {
				_, err = GetContext(ctx, "synthetic", "user")
			} else {
				err = SetContext(ctx, "synthetic", "user", "value")
			}
			if !errors.Is(err, context.DeadlineExceeded) {
				t.Fatal(err)
			}
			if observedCommand.ProcessState == nil || observedCommand.ProcessState.Success() {
				t.Fatal("child not reaped")
			}
		})
	}
}
func TestSetValidatesSizeBeforeCreatingChild(t *testing.T) {
	selectedMode = "hang"
	before := spawnRequests
	err := SetContext(context.Background(), "synthetic", "user", strings.Repeat("x", 5000))
	if !errors.Is(err, ErrSetDataTooBig) || spawnRequests != before {
		t.Fatal("oversize request spawned a child")
	}
}
func TestSetStdinCompletionAndEarlyExitAreJoined(t *testing.T) {
	for _, mode := range []string{"stdin", "exit"} {
		selectedMode = mode
		ctx, cancel := context.WithTimeout(context.Background(), time.Second)
		err := SetContext(ctx, "synthetic with space", "user'quoted", "synthetic\n中文")
		cancel()
		if mode == "stdin" && err != nil {
			t.Fatal(err)
		}
		if mode == "exit" && err == nil {
			t.Fatal("early exit accepted")
		}
		if observedCommand.ProcessState == nil {
			t.Fatal("child not reaped")
		}
	}
}
func TestCancelledSetDoesNotSpawn(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	before := spawnRequests
	if err := SetContext(ctx, "synthetic", "user", "value"); !errors.Is(err, context.Canceled) || spawnRequests != before {
		t.Fatal("cancelled request spawned")
	}
}
