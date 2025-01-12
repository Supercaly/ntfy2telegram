# ntfy2telegram

Forward ntfy.sh Push Messages to Telegram Using Telegram Bots 🤖  

When self-hosting a server, staying instantly informed about any events affecting it—such as script failures, backup errors, or UPS power outages—is crucial. **ntfy** allows you to send push notifications to various devices effortlessly via simple HTTP POST requests.

**ntfy.sh** provides its own [Android application](https://docs.ntfy.sh/#step-1-get-the-app) for receiving push notifications. However, the app continuously polls the notification server to retrieve messages, which can significantly drain the battery.  
Additionally, if we self-host an ntfy server and keep it inaccessible from outside our home network, the ntfy Android app cannot receive messages.  

Yes, it's possible to use Firebase Cloud Messaging (FCM) for this purpose, but in the case of self-hosting, we must manually recompile the application by following this [guide](https://docs.ntfy.sh/develop/?h=fcm#build-play-flavor-fcm).

Receiving messages directly on Telegram is convenient and straightforward. Many people already use it as a notification system for their scripts, and it’s one less app to install.

This application is inspired by [ntfy-sh-listener](https://github.com/sanwebinfo/ntfy-sh-listener), extending it and adding more features.

## Setup

This application is intended to be used with Docker or docker compose 🐳.

Download or Clone the repository via git

```console
$ git clone https://github.com/Supercaly/ntfy2telegram
$ cd ntfy2telegram
```

Edit the content of the `compose.yaml` file and add all the required environment variables. 
Then run docker compose with 

```console
$ docker compose up -d
```

## Environment Variables

| Variable | Required | Value |
|--|--|--|
| NTFY_WS_PROTOCOL | No | The websocket protocol to use for the connection. Can be either `ws` or `wss` (recommended `wss`). Default `ws` |
| NTFY_SERVER_ADDRESS | Yes | Address of the NTFY server. Can be a pair ip:port or a dns name. Example `127.0.0.1:80` or `ntfy.sh:8080`. |
| NTFY_TOPIC | Yes | NTFY topic to listen for messages. Example `test-topic`. |
| NTFY_USERNAME | No | Username of an existing ntfy user if the server has Access Control List (ACL) enabled. [More details](https://docs.ntfy.sh/config/?h=acl#access-control-list-acl). |
| NTFY_PASSWORD | No | Password of an existing user if ACL is enabled. As stated in [here](https://docs.ntfy.sh/publish/#username-password) the Basic Authorization takes a base64 encoded string with "<username>:<password>". If you specify both `NTFY_USERNAME` and `NTFY_PASSWORD` we will encode the string for you; otherwise you can create it yourself and pass it to `NTFY_PASSWORD` without setting `NTFY_USERNAME`. Remember that the string is only base64 encoded and it is not encrypted. |
| NTFY_TOKEN | No | NTFY access token if ACL is enabled. Use this instead of `NTFY_USERNAME` and `NTFY_PASSWORD` for [added security](https://docs.ntfy.sh/config/?h=acl#access-tokens). |
| TG_BOT_TOKEN | Yes | Token for the telegram bot. |
| TG_CHAT_ID | Yes | Telegram Chat ID. Follow [this guide](https://docs.tracardi.com/qa/how_can_i_get_telegram_bot/) to obtain your token and chat id. |

## Supported messages

When [sending a message](https://docs.ntfy.sh/publish) to a ntfy topic different elements can be passed along.
The table below shows all the message fields supported by the application

- Message title
- Tags & Emojis (the tags matching the [emoji code list](https://docs.ntfy.sh/emojis/) are converted into emojis)
- Markdown formatting
- Click action

## TODO

- [ ] Listen for multiple topics at the same time.
- [ ] Handle message priority with an icon like NTFY app.
- [ ] Handle message attachments.
- [ ] Handle message actions.
- [ ] Handle icons.