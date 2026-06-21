// +build ignore

package main

import (
	"fmt"
	"os"
	"os/exec"
)

func main() {
	cmds := [][]string{
		{"protoc", "--go_out=.", "--go_opt=paths=source_relative",
			"--go-grpc_out=.", "--go-grpc_opt=paths=source_relative",
			"proto/trade_execution.proto"},
	}
	for _, args := range cmds {
		cmd := exec.Command(args[0], args[1:]...)
		cmd.Stdout = os.Stdout
		cmd.Stderr = os.Stderr
		if err := cmd.Run(); err != nil {
			fmt.Fprintf(os.Stderr, "error running %v: %v\n", args, err)
			os.Exit(1)
		}
	}
}