FROM golang:1.25-alpine

WORKDIR /app

COPY . .

RUN go mod init simple-file-share
RUN go mod tidy
RUN go build -o app

EXPOSE 8080
CMD ["./app"]
