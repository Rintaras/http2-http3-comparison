FROM golang:1.21 AS builder

WORKDIR /app

# HTTP/3クライアントのビルド
COPY router/go.mod ./router/
COPY router/http3_client.go ./router/
WORKDIR /app/router
RUN go mod download && go mod tidy && go build -o http3_client http3_client.go

# サーバーのビルド
WORKDIR /app
COPY server/go.mod ./
RUN go mod download

COPY server/main.go ./
RUN go mod tidy && CGO_ENABLED=0 GOOS=linux go build -a -o main .

FROM ubuntu:22.04

RUN apt-get update && apt-get install -y ca-certificates iproute2 && rm -rf /var/lib/apt/lists/*

WORKDIR /root/

COPY --from=builder /app/main .
COPY --from=builder /app/router/http3_client .
COPY certs/localhost+2.pem .
COPY certs/localhost+2-key.pem .
COPY scripts/tc_setup.sh .
RUN chmod +x tc_setup.sh http3_client

EXPOSE 8443

CMD ["./main"]
