// Copyright 2026 Alibaba Group
// SPDX-License-Identifier: Apache-2.0
// Worker declarations below are copied byte-for-byte from official DWS v1.0.67.
// This standalone probe uses only a synthetic child; never runs DWS or security.
// NewUnavailableError is a local wrapping stub, not the official classification.
package keychainprobe

import (
 "bufio"
 "context"
 "errors"
 "fmt"
 "io"
 "os"
 "os/exec"
 "syscall"
 "testing"
 "time"
)

func NewUnavailableError(operation string, err error) error {
 return fmt.Errorf("%s: %w", operation, err)
}

type darwinKeychainResult struct {
	key []byte
	err error
}

type darwinKeychainWorker struct {
	result <-chan darwinKeychainResult
	done   <-chan struct{}
}

func startDarwinKeychainWorker(operation string, work func() ([]byte, error)) darwinKeychainWorker {
	result := make(chan darwinKeychainResult, 1)
	done := make(chan struct{})
	go func() {
		defer close(done)
		defer func() {
			if recovered := recover(); recovered != nil {
				result <- darwinKeychainResult{
					err: NewUnavailableError(operation, fmt.Errorf("panic: %v", recovered)),
				}
			}
		}()
		key, err := work()
		result <- darwinKeychainResult{key: key, err: err}
	}()
	return darwinKeychainWorker{result: result, done: done}
}

func waitDarwinKeychainWorker(timeout time.Duration, operation string, worker darwinKeychainWorker) ([]byte, error, <-chan struct{}) {
	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()

	select {
	case result := <-worker.result:
		<-worker.done
		return result.key, result.err, worker.done
	case <-ctx.Done():
		return nil, NewUnavailableError(operation, ctx.Err()), worker.done
	}
}

func TestSyntheticWaitChild(t *testing.T) {
 if os.Getenv("DAB_SYNTHETIC_WAIT_CHILD") != "1" { t.Skip("helper only") }
 fmt.Println("synthetic-ready")
 _, _ = io.Copy(io.Discard, os.Stdin)
}

func TestOfficialWaitTimeoutLeavesOwnedChildAlive(t *testing.T) {
 cmd := exec.Command(os.Args[0], "-test.run=^TestSyntheticWaitChild$")
 cmd.Env = append(os.Environ(), "DAB_SYNTHETIC_WAIT_CHILD=1")
 stdin, err := cmd.StdinPipe()
 if err != nil { t.Fatal(err) }
 defer stdin.Close()
 stdout, err := cmd.StdoutPipe()
 if err != nil { t.Fatal(err) }
 if err = cmd.Start(); err != nil { t.Fatal(err) }
 worker := startDarwinKeychainWorker("synthetic child", func() ([]byte,error) { return nil,cmd.Wait() })
 defer func() {
  _ = cmd.Process.Kill()
  select { case <-worker.done: case <-time.After(2*time.Second): t.Error("owned synthetic child was not reaped") }
 }()
 ready := make(chan string,1)
 go func(){s:=bufio.NewScanner(stdout); if s.Scan(){ready<-s.Text()} else {ready<-""}}()
 select {
 case line:=<-ready: if line!="synthetic-ready" {t.Fatalf("unexpected helper: %q",line)}
 case <-time.After(2*time.Second): t.Fatal("helper did not start")
 }
 _, err, done := waitDarwinKeychainWorker(30*time.Millisecond, "synthetic child", worker)
 if !errors.Is(err,context.DeadlineExceeded) {t.Fatalf("expected timeout, got %v",err)}
 select {case <-done:t.Fatal("worker unexpectedly stopped at timeout");default:}
 if err=cmd.Process.Signal(syscall.Signal(0)); err!=nil {t.Fatalf("child should still be alive: %v",err)}
 t.Log("reproduced: official wait returned timeout while owned synthetic child remained alive")
}

func TestOfficialWaitNormalCompletion(t *testing.T) {
 worker:=startDarwinKeychainWorker("synthetic",func()([]byte,error){return []byte("synthetic-value"),nil})
 value,err,done:=waitDarwinKeychainWorker(time.Second,"synthetic",worker)
 if err!=nil || string(value)!="synthetic-value" {t.Fatalf("unexpected completion: %q %v",value,err)}
 select{case <-done:default:t.Fatal("completed worker not joined")}
}
