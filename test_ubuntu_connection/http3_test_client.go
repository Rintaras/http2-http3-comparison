package main

import (
	"crypto/tls"
	"fmt"
	"log"
	"net/http"
	"time"

	"github.com/quic-go/quic-go/http3"
)

func main() {
	roundTripper := &http3.RoundTripper{
		TLSClientConfig: &tls.Config{
			InsecureSkipVerify: true,
		},
	}
	defer roundTripper.Close()

	client := &http.Client{
		Transport: roundTripper,
	}

	start := time.Now()
	resp, err := client.Get("https://192.168.100.60:8443/1mb")
	if err != nil {
		log.Fatalf("HTTP/3 request failed: %v", err)
	}
	defer resp.Body.Close()

	duration := time.Since(start)
	fmt.Printf("H3: %.6fs (Status: %s)\n", duration.Seconds(), resp.Status)
}
