# ntfy2telegram

Forward ntfy.sh Push Messages to Telegram Using Telegram Bots 🤖  

When self-hosting a server, staying instantly informed about any events affecting it—such as script failures, backup errors, or UPS power outages—is crucial. **ntfy** allows you to send push notifications to various devices effortlessly via simple HTTP POST requests.

Receiving messages directly on Telegram is convenient and straightforward. Many people already use it as a notification system for their scripts, and it’s one less app to install.

This application is inspired by [ntfy-sh-listener](https://github.com/sanwebinfo/ntfy-sh-listener), extending it and adding more features.

> **ntfy.sh** provides its own [Android application](https://docs.ntfy.sh/#step-1-get-the-app) for receiving push notifications. However, the app continuously polls the notification server to retrieve messages, which can significantly drain the battery.
Additionally, if we self-host an ntfy server and keep it inaccessible from outside our home network, the ntfy Android app cannot receive messages.
It's possible to use Firebase Cloud Messaging (FCM) for this purpose, but in the case of self-hosting, we must manually recompile the application by following this [guide](https://docs.ntfy.sh/develop/?h=fcm#build-play-flavor-fcm).

## Setup with Docker 🐳

Pull the image using

```console
$ docker pull ghcr.io/supercaly/ntfy2telegram:main
```

Run the image in docker using

```console
$ docker run -d \
    --restart always \
    -e NTFY_WS_PROTOCOL="ws" \
    -e NTFY_SERVER_ADDRESS="<ntfy-server-ip:port>" \
    -e NTFY_TOPIC="<your-topic>" \
    -e NTFY_TOKEN="<ntfy-token>" \
    -e NTFY_USERNAME="<ntfy-username>" \
    -e NTFY_PASSWORD="<ntfy-password>" \
    -e NTFY_INCLUDE_TOPIC="True" \
    -e TG_CHAT_ID="<telegram-chat-id>" \
    -e TG_BOT_TOKEN="<telegram-bot-token>" \
    --name ntfy2tg-<topic> \
    ntfy2telegram:main
```

or with **docker compose** by creating a `compose.yaml` file:

```yaml
services:
  server:
    image: "ghcr.io/supercaly/ntfy2telegram:main"
    restart: always

    # define env variables directly in the compose file
    environment:
      - NTFY_WS_PROTOCOL="ws"
      - NTFY_SERVER_ADDRESS="<ntfy-server-ip:port>"
      - NTFY_TOPIC="<your-topic>"
      - NTFY_TOKEN="<ntfy-token>"
      - NTFY_USERNAME="<ntfy-username>"
      - NTFY_PASSWORD="<ntfy-password>"
      - NTFY_INCLUDE_TOPIC="True"
      - TG_CHAT_ID="<telegram-chat-id>"
      - TG_BOT_TOKEN="<telegram-bot-token>"

    # store env variables in a separate .env file (recommended for secrets)
    env_file:
      - .env
```

> Note: If you intend to use **Portainer** remember to substitute `.env` with `stack.env`.

## Manual install 🛠️

This application is intended to be used with Docker but you can use it directly on your machine by building it by hand.

Download or clone the repository via git:

```console
$ git clone https://github.com/Supercaly/ntfy2telegram
$ cd ntfy2telegram
```

Export the environment variables then run the application with

```console
$ python app.py
```

If you intend in running this application permanently you should export the environment variables into your `.*rc` file and create a systemd service that runs on boot.

## Environment Variables 🌐

| Variable | Required | Default | Description |
|--|--|--|--|
| NTFY_WS_PROTOCOL | No | `ws` | The websocket protocol to use for the connection. Can be either `ws` or `wss` (recommended `wss`). |
| NTFY_SERVER_ADDRESS | Yes | - | Address of the NTFY server. Can be a pair `ip:port` or a dns name. Example `127.0.0.1:80` or `ntfy.sh:8080`. |
| NTFY_TOPIC | Yes | - | Comma-separated list of NTFY topic to listen for messages. Example `topic1,topic2,topic3`. |
| NTFY_USERNAME | No | - | Username of an existing ntfy user if the server has Access Control List (ACL) enabled. [More details](https://docs.ntfy.sh/config/?h=acl#access-control-list-acl). |
| NTFY_PASSWORD | No | - | Password of an existing user if ACL is enabled. As stated in [here](https://docs.ntfy.sh/publish/#username-password) the Basic Authorization takes a base64 encoded string with "<username>:<password>". If you specify both `NTFY_USERNAME` and `NTFY_PASSWORD` we will encode the string for you; otherwise you can create it yourself and pass it to `NTFY_PASSWORD` without setting `NTFY_USERNAME`. Remember that the string is only base64 encoded and it is not encrypted. |
| NTFY_TOKEN | No | - | NTFY access token if ACL is enabled. Use this instead of `NTFY_USERNAME` and `NTFY_PASSWORD` for [added security](https://docs.ntfy.sh/config/?h=acl#access-tokens). |
| NTFY_INCLUDE_TOPIC | No | `False` | If set to `True` will include the name of the topic with every message sent to telegram. This is useful to distinguish between different topics sent to the same chat. |
| TG_BOT_TOKEN | Yes | - | Token for the telegram bot. |
| TG_CHAT_ID | Yes | - | Telegram Chat ID. Follow [this guide](https://docs.tracardi.com/qa/how_can_i_get_telegram_bot/) to obtain your token and chat id. |

## Supported messages 🔔

When [sending a message](https://docs.ntfy.sh/publish) to a ntfy topic different elements can be passed along.
The list below shows all the message fields supported by the application

- Message title
- Tags & Emojis (the tags matching the [emoji code list](https://docs.ntfy.sh/emojis/) are converted into emojis)
- Markdown formatting
- Click action

## TODO 📋

- [x] Listen for multiple topics at the same time.
- [x] Report the topic along with the message (useful when there are more topics sent to the same bot).
- [ ] Handle message priority with an icon like NTFY app.
- [ ] Handle message attachments.
- [ ] Handle message actions.
- [ ] Handle icons.
