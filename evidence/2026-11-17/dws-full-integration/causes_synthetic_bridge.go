//go:build darwin && dab_synthetic

package keyring
import ("context";"os/exec")
func SetSyntheticCommandForTest(fn func(context.Context,string,...string)*exec.Cmd) func(){
 old:=keychainCommandContext;keychainCommandContext=fn
 return func(){keychainCommandContext=old}
}
