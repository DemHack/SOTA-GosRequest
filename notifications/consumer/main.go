package main

import (
	"encoding/json"
	"fmt"
	"os"
	"strconv"
	"sync"

	"github.com/aws/aws-lambda-go/events"
	"github.com/aws/aws-lambda-go/lambda"
	tgbotapi "github.com/go-telegram-bot-api/telegram-bot-api/v5"
)

var (
	botToken    = os.Getenv("BOT_TOKEN")
	debugChatID = os.Getenv("DEBUG_CHAT")
)

type Notification struct {
	ChatID  int64  `json:"chatID"`
	Message string `json:"message"`
}

func formatDebugMessage(chatID int64, text string) string {
	return fmt.Sprintf("Chat: `%d`\nMessage: %s", chatID, text)
}

func sendMessage(bot *tgbotapi.BotAPI, chatId int64, text string) error {
	m := tgbotapi.NewMessage(chatId, text)
	m.ParseMode = "MARKDOWN"

	_, err := bot.Send(m)
	if err != nil {
		return err
	}
	fmt.Printf("message sent %d\n", chatId)
	return nil
}

func processNotification(bot *tgbotapi.BotAPI, n Notification) error {
	wg := sync.WaitGroup{}
	wg.Add(2)

	c := make(chan error, 1)

	go func() {
		err := sendMessage(bot, n.ChatID, n.Message)
		c <- err
		wg.Done()
	}()

	go func() {
		chatID, _ := strconv.ParseInt(debugChatID, 10, 64)
		_ = sendMessage(bot, chatID, formatDebugMessage(n.ChatID, n.Message))
		wg.Done()
	}()

	wg.Wait()
	return <-c
}

func createHandler(bot *tgbotapi.BotAPI) func(events.SQSEvent) (events.SQSEventResponse, error) {
	return func(req events.SQSEvent) (events.SQSEventResponse, error) {
		broken := make(chan string, len(req.Records))
		wg := sync.WaitGroup{}
		wg.Add(len(req.Records))

		for _, record := range req.Records {
			record := record

			go func() {
				n := Notification{}
				if err := json.Unmarshal([]byte(record.Body), &n); err != nil {
					fmt.Printf("failed to unmarshal %s %s\n", record.MessageId, err)
					broken <- record.MessageId
					wg.Done()
					return
				}

				if err := processNotification(bot, n); err != nil {
					fmt.Printf("failed to nofy %s %d %s\n", record.MessageId, n.ChatID, err)
					broken <- record.MessageId
					wg.Done()
					return
				}

				broken <- ""
				wg.Done()
			}()
		}

		wg.Wait()
		close(broken)

		var result []events.SQSBatchItemFailure
		for id := range broken {
			if id != "" {
				result = append(result, events.SQSBatchItemFailure{ItemIdentifier: id})
			}
		}

		return events.SQSEventResponse{BatchItemFailures: result}, nil
	}
}

func main() {
	bot, err := tgbotapi.NewBotAPI(botToken)
	if err != nil {
		panic(err)
	}
	lambda.Start(createHandler(bot))
}
