package main

import (
	"context"

	"github.com/aws/aws-lambda-go/events"
	"github.com/aws/aws-lambda-go/lambda"
	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/sqs"
)

var (
	queueURL = aws.String("https://sqs.eu-central-1.amazonaws.com/136160194617/gosreq-notifications")
)

type Response struct {
	StatusCode int    `json:"statusCode"`
	Body       string `json:"body"`
}

func createHandler(sess *session.Session) func(context.Context, events.APIGatewayV2HTTPRequest) (Response, error) {
	return func(ctx context.Context, api events.APIGatewayV2HTTPRequest) (Response, error) {
		svc := sqs.New(sess)
		_, err := svc.SendMessage(&sqs.SendMessageInput{
			MessageBody: aws.String(api.Body),
			QueueUrl:    queueURL,
		})

		if err != nil {
			return Response{}, err
		}
		return Response{Body: "OK", StatusCode: 200}, nil
	}
}

func main() {
	sess := session.Must(session.NewSessionWithOptions(session.Options{
		Config: aws.Config{
			Region: aws.String("eu-central-1"),
		},
	}))
	lambda.Start(createHandler(sess))
}
