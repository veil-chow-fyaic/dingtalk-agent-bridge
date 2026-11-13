// Copyright 2026 OpenAI
// SPDX-License-Identifier: Apache-2.0
// Synthetic-only tests for the candidate patched official Darwin functions.
package keychain

import (
	"bytes"
	"context"
	"encoding/base64"
	"errors"
	"fmt"
	keyring "github.com/zalando/go-keyring"
	"os"
	"os/exec"
	"strings"
	"sync/atomic"
	"testing"
	"time"
)

func TestMain(m *testing.M) {
	// Fail closed: no test may reach the real system backend or official TestMain.
	readDefaultKeychain = func(context.Context) ([]byte, error) { panic("real preflight forbidden") }
	keyringGet = func(context.Context, string, string) (string, error) { panic("real read forbidden") }
	keyringSet = func(context.Context, string, string, string) error { panic("real write forbidden") }
	os.Exit(m.Run())
}
func TestSyntheticChild(t *testing.T) {
	if os.Getenv("DAB_CANCEL_CHILD") != "1" {
		t.Skip("helper only")
	}
	fmt.Println("synthetic child")
	for {
		time.Sleep(time.Hour)
	}
}
func fixture() darwinKeychainRuntime {
	return darwinKeychainRuntime{
		timeout:        time.Second,
		checkAvailable: func(context.Context) error { return nil },
		get: func(context.Context, string, string) (string, error) {
			return base64.StdEncoding.EncodeToString(bytes.Repeat([]byte{7}, 32)), nil
		},
		set:      func(context.Context, string, string, string) error { panic("unexpected write") },
		randRead: func(b []byte) (int, error) { return copy(b, bytes.Repeat([]byte{9}, 32)), nil },
	}
}
func joined(t *testing.T, done <-chan struct{}) {
	t.Helper()
	select {
	case <-done:
	default:
		t.Fatal("worker was not joined")
	}
}
func child(ctx context.Context) (*exec.Cmd, error) {
	cmd := exec.CommandContext(ctx, os.Args[0], "-test.run=^TestSyntheticChild$")
	cmd.Env = append(os.Environ(), "DAB_CANCEL_CHILD=1")
	cmd.WaitDelay = time.Second
	return cmd, cmd.Run()
}
func TestReadSuccessNoWriteAndJoined(t *testing.T) {
	r := fixture()
	key, err, done := getSystemDEKReadOnlyWithRuntime("synthetic", r)
	if err != nil || !bytes.Equal(key, bytes.Repeat([]byte{7}, 32)) {
		t.Fatalf("unexpected result %v", err)
	}
	joined(t, done)
}
func TestNotFoundIsMissingButArbitraryFailureIsUnavailable(t *testing.T) {
	for _, tc := range []struct {
		err     error
		missing bool
	}{{keyring.ErrNotFound, true}, {errors.New("synthetic access denied"), false}} {
		r := fixture()
		r.get = func(context.Context, string, string) (string, error) { return "", tc.err }
		_, err, done := getSystemDEKReadOnlyWithRuntime("synthetic", r)
		joined(t, done)
		if IsDEKMissing(err) != tc.missing || IsUnavailable(err) == tc.missing {
			t.Fatalf("classification: %v", err)
		}
	}
}
func TestCreateOnNotFoundAndRejectUnavailable(t *testing.T) {
	r := fixture()
	stored := ""
	calls := 0
	writes := 0
	r.get = func(context.Context, string, string) (string, error) {
		calls++
		if stored == "" {
			return "", keyring.ErrNotFound
		}
		return stored, nil
	}
	r.set = func(_ context.Context, _, _, value string) error { writes++; stored = value; return nil }
	key, err, done := getOrCreateDEKWithRuntime("synthetic", r)
	joined(t, done)
	if err != nil || len(key) != 32 || calls != 2 || writes != 1 {
		t.Fatalf("create/readback %v calls=%d writes=%d", err, calls, writes)
	}
	r = fixture()
	r.get = func(context.Context, string, string) (string, error) { return "", errors.New("ambiguous failure") }
	_, err, done = getOrCreateDEKWithRuntime("synthetic", r)
	joined(t, done)
	if !IsUnavailable(err) {
		t.Fatal(err)
	}
}
func TestTimeoutCancelsAndReapsPreflightReadAndWriteChild(t *testing.T) {
	for _, stage := range []string{"preflight", "get", "set"} {
		t.Run(stage, func(t *testing.T) {
			r := fixture()
			r.timeout = 200 * time.Millisecond
			var cmd *exec.Cmd
			var reads, writes atomic.Int32
			run := func(ctx context.Context) error { var err error; cmd, err = child(ctx); return err }
			switch stage {
			case "preflight":
				r.checkAvailable = run
				r.get = func(context.Context, string, string) (string, error) { reads.Add(1); return "", nil }
			case "get":
				r.get = func(ctx context.Context, _, _ string) (string, error) { return "", run(ctx) }
			case "set":
				r.get = func(context.Context, string, string) (string, error) { reads.Add(1); return "", keyring.ErrNotFound }
				r.set = func(ctx context.Context, _, _, _ string) error { writes.Add(1); return run(ctx) }
			}
			started := time.Now()
			_, err, done := getOrCreateDEKWithRuntime("synthetic", r)
			joined(t, done)
			if !IsUnavailable(err) || !errors.Is(err, context.DeadlineExceeded) {
				t.Fatalf("deadline classification %v", err)
			}
			if time.Since(started) > 2*time.Second {
				t.Fatal("cleanup exceeded bound")
			}
			if cmd == nil || cmd.ProcessState == nil || cmd.ProcessState.Success() {
				t.Fatal("owned synthetic child not reaped")
			}
			if stage == "preflight" && reads.Load() != 0 {
				t.Fatal("read after expired preflight")
			}
			if stage == "set" && (reads.Load() != 1 || writes.Load() != 1) {
				t.Fatal("automatic retry after expired write")
			}
		})
	}
}
func TestOneDeadlineIncludesPreflightAndSubsequentRead(t *testing.T) {
	r := fixture()
	r.timeout = 100 * time.Millisecond
	var first time.Time
	r.checkAvailable = func(ctx context.Context) error {
		first, _ = ctx.Deadline()
		time.Sleep(30 * time.Millisecond)
		return nil
	}
	r.get = func(ctx context.Context, _, _ string) (string, error) {
		last, _ := ctx.Deadline()
		if !last.Equal(first) {
			return "", errors.New("deadline reset")
		}
		<-ctx.Done()
		return "", ctx.Err()
	}
	_, err, done := getSystemDEKReadOnlyWithRuntime("synthetic", r)
	joined(t, done)
	if !errors.Is(err, context.DeadlineExceeded) {
		t.Fatal(err)
	}
}
func TestCancelledPreflightCannotFallThroughOnOrdinaryNilError(t *testing.T) {
	r := fixture()
	r.timeout = 20 * time.Millisecond
	r.checkAvailable = func(ctx context.Context) error { <-ctx.Done(); return nil }
	r.get = func(context.Context, string, string) (string, error) { panic("late read") }
	_, err, done := getSystemDEKReadOnlyWithRuntime("synthetic", r)
	joined(t, done)
	if !errors.Is(err, context.DeadlineExceeded) {
		t.Fatal(err)
	}
}
func TestUncooperativeWorkerReportsPendingAndCannotWriteAfterLateRead(t *testing.T) {
	prior := keychainCleanupTimeout
	keychainCleanupTimeout = 30 * time.Millisecond
	defer func() { keychainCleanupTimeout = prior }()
	release := make(chan struct{})
	r := fixture()
	r.timeout = 20 * time.Millisecond
	var writes atomic.Int32
	r.get = func(context.Context, string, string) (string, error) { <-release; return "", keyring.ErrNotFound }
	r.set = func(context.Context, string, string, string) error { writes.Add(1); return nil }
	_, err, done := getOrCreateDEKWithRuntime("synthetic", r)
	if !IsUnavailable(err) || !errors.Is(err, context.DeadlineExceeded) || !errors.Is(err, errDarwinCleanupPending) {
		t.Fatal(err)
	}
	select {
	case <-done:
		t.Fatal("claimed incomplete worker done")
	default:
	}
	close(release)
	select {
	case <-done:
	case <-time.After(time.Second):
		t.Fatal("late worker did not finish")
	}
	if writes.Load() != 0 {
		t.Fatal("write after cancelled read")
	}
}
func TestExpiredContextCannotAcceptAlreadyQueuedSuccess(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	worker := startDarwinKeychainWorker("synthetic", func() ([]byte, error) { return []byte("late"), nil })
	<-worker.done
	key, err, done := waitDarwinKeychainWorker(ctx, "synthetic", worker)
	joined(t, done)
	if key != nil || !errors.Is(err, context.Canceled) {
		t.Fatal("late success escaped deadline")
	}
}
func TestPreflightCommandCancellationIsNotIgnored(t *testing.T) {
	prior := readDefaultKeychain
	defer func() { readDefaultKeychain = prior }()
	readDefaultKeychain = func(ctx context.Context) ([]byte, error) { <-ctx.Done(); return nil, ctx.Err() }
	ctx, cancel := context.WithTimeout(context.Background(), 20*time.Millisecond)
	defer cancel()
	if err := checkDefaultKeychainAvailable(ctx); !IsUnavailable(err) || !errors.Is(err, context.DeadlineExceeded) {
		t.Fatal(err)
	}
}
func TestPanicRemainsUnavailableAndJoined(t *testing.T) {
	r := fixture()
	r.checkAvailable = func(context.Context) error { panic("synthetic panic") }
	_, err, done := getSystemDEKReadOnlyWithRuntime("synthetic", r)
	joined(t, done)
	if !IsUnavailable(err) || !strings.Contains(err.Error(), "synthetic panic") {
		t.Fatal(err)
	}
}
