// OGAS-Dispatcher：控制面协调中枢。
// 首版从 Multica fork，改动集中在四处：liskin runtime 注册、状态事件引出、
// ask 双向通道、API facade。上游同步流程见 REBASE.md。
package main

import (
	"log"
	"net/http"
)

func health(w http.ResponseWriter, _ *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.Write([]byte(`{"ok":true,"service":"dispatcher"}`))
}

func main() {
	http.HandleFunc("/health", health)
	addr := ":8080"
	log.Printf("dispatcher listening on %s", addr)
	if err := http.ListenAndServe(addr, nil); err != nil {
		log.Fatal(err)
	}
}
