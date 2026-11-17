//go:build darwin && dab_synthetic

// Copyright 2026 OpenAI
// SPDX-License-Identifier: Apache-2.0
package keychain

import (
 "bytes"
 "context"
 "encoding/base64"
 "errors"
 "io"
 "os"
 "os/exec"
 "strings"
 "testing"
 "time"
 keyring "github.com/zalando/go-keyring"
)

func TestSyntheticIntegratedChild(t *testing.T) {
 mode:=os.Getenv("DAB_INTEGRATED_CHILD")
 if mode=="" { t.Skip("helper only") }
 switch mode {
 case "hang": for {time.Sleep(time.Hour)}
 case "missing": os.Stderr.WriteString("could not be found\n");os.Exit(44)
 case "value": os.Stdout.WriteString(base64.StdEncoding.EncodeToString(bytes.Repeat([]byte{9},32))+"\n")
 case "write":
  data,err:=io.ReadAll(os.Stdin)
  if err!=nil || !strings.HasPrefix(string(data),"add-generic-password -U -s ") || !strings.HasSuffix(string(data),"\n") {os.Exit(23)}
 default: os.Exit(24)
 }
 os.Exit(0)
}

func integratedRuntime(t *testing.T, modes []string) (darwinKeychainRuntime,*[]*exec.Cmd) {
 t.Helper()
 commands:=[]*exec.Cmd{}
 restore:=keyring.SetSyntheticCommandForTest(func(ctx context.Context,program string,args ...string)*exec.Cmd{
  if program!="/usr/bin/security" {panic("unexpected executable")}
  if !(len(args)==1&&args[0]=="-i") && !(len(args)==5&&args[0]=="find-generic-password") {panic("unexpected arguments")}
  n:=len(commands);if n>=len(modes) {panic("unexpected retry or write")}
  cmd:=exec.CommandContext(ctx,os.Args[0],"-test.run=^TestSyntheticIntegratedChild$")
  cmd.Env=append(os.Environ(),"DAB_INTEGRATED_CHILD="+modes[n]);commands=append(commands,cmd)
  return cmd
 })
 t.Cleanup(restore)
 r:=fixture();r.get=keyring.GetContext;r.set=keyring.SetContext;r.timeout=2*time.Second
 return r,&commands
}
func assertIntegratedReaped(t *testing.T,commands []*exec.Cmd,want int){
 t.Helper();if len(commands)!=want {t.Fatalf("commands=%d want=%d",len(commands),want)}
 for _,cmd:=range commands {if cmd.Process==nil||cmd.ProcessState==nil {t.Fatal("owned command was not started and waited")}}
}
func TestIntegratedDWSAndKeyringNormalReadAndCreate(t *testing.T){
 for _,tc:=range []struct{name string;create bool;modes []string}{{"read",false,[]string{"value"}},{"create",true,[]string{"missing","write","value"}}}{
  t.Run(tc.name,func(t *testing.T){
   r,commands:=integratedRuntime(t,tc.modes)
   var key []byte;var err error;var done <-chan struct{}
   if tc.create {key,err,done=getOrCreateDEKWithRuntime("synthetic-integration",r)} else {key,err,done=getSystemDEKReadOnlyWithRuntime("synthetic-integration",r)}
   if err!=nil||!bytes.Equal(key,bytes.Repeat([]byte{9},32)){t.Fatalf("normal result err=%v length=%d",err,len(key))}
   joined(t,done);assertIntegratedReaped(t,*commands,len(tc.modes))
  })
 }
}
func TestIntegratedDWSAndKeyringCancelReadAndWrite(t *testing.T){
 for _,tc:=range []struct{name string;create bool;modes []string}{{"read",false,[]string{"hang"}},{"write",true,[]string{"missing","hang"}}}{
  t.Run(tc.name,func(t *testing.T){
   r,commands:=integratedRuntime(t,tc.modes);r.timeout=300*time.Millisecond
   var err error;var done <-chan struct{}
   if tc.create {_,err,done=getOrCreateDEKWithRuntime("synthetic-integration",r)} else {_,err,done=getSystemDEKReadOnlyWithRuntime("synthetic-integration",r)}
   if !IsUnavailable(err)||!errors.Is(err,context.DeadlineExceeded)||errors.Is(err,errDarwinCleanupPending){t.Fatalf("cancellation result %v",err)}
   joined(t,done);assertIntegratedReaped(t,*commands,len(tc.modes))
  })
 }
}
