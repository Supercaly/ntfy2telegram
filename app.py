import base64
from dotenv import dotenv_values
from emoji import rawEmojis as emoji_map
from emoji import priorityEmojis as priority_emoji
import json
import logging
from md2tgmd import escape
import os
import requests
import websocket

# setup default logger
# TODO: logger shows also websocket messages
logging.basicConfig(
    format='%(asctime)s: %(levelname)s: %(message)s',
)
logger = logging.getLogger(__name__)

# global environment
class Env:
    def load_from_env(self):
        # combine variables from environment and .env files
        env_vars = {
            **dotenv_values(".env"),
            **os.environ,
        }

        # NTFY websocket protocol [ws,wss]
        self.ntfy_ws_protocol = env_vars.get('NTFY_WS_PROTOCOL', 'ws')
        if self.ntfy_ws_protocol != "ws" and self.ntfy_ws_protocol != "wss":
            raise Exception(f"invalid 'NTFY_WS_PROTOCOL': '{self.ntfy_ws_protocol}'")
        # NTFY server address
        self.ntfy_address = env_vars.get('NTFY_SERVER_ADDRESS')
        if self.ntfy_address is None:
            raise Exception(f"environment variable 'NTFY_SERVER_ADDRESS' is undefined")
        # NTFY topic
        self.ntfy_topic = env_vars.get('NTFY_TOPIC')
        if self.ntfy_topic is None:
            raise Exception(f"environment variable 'NTFY_TOPIC' is undefined")
        # NTFY ACL credentials
        self.ntfy_username = env_vars.get('NTFY_USERNAME')
        self.ntfy_password = env_vars.get('NTFY_PASSWORD')
        self.ntfy_token = env_vars.get('NTFY_TOKEN')
        # include topic in message
        # TODO: Convert to bool
        self.ntfy_include_topic = env_vars.get('NTFY_INCLUDE_TOPIC','False')
        # include priority in message
        # TODO: Convert to bool
        self.ntfy_include_priority = env_vars.get('NTFY_INCLUDE_PRIORITY','False')

        # Telegram chat id
        self.tg_chat_id = env_vars.get('TG_CHAT_ID')
        if self.tg_chat_id is None:
            raise Exception(f"environment variable 'TG_CHAT_ID' is undefined")
        # Telegram bot token
        self.tg_token = env_vars.get('TG_BOT_TOKEN')
        if self.tg_token is None:
            raise Exception(f"environment variable 'TG_BOT_TOKEN' is undefined")

        # app log level
        self.log_level = env_vars.get('LOG_LEVEL','INFO')

    def get_ws_address(self) -> str:
        """
        Return the full address for the NTFY websocket.
        """
        return f"{self.ntfy_ws_protocol}://{self.ntfy_address}/{self.ntfy_topic}/ws"

    def topic_list(self) -> list[str]:
        """
        Return the NTFY topics as a list
        """
        return self.ntfy_topic.split(',')
env = None

###################################
# message parsing and sending utils
###################################
def escape_markdown_v2(text: str) -> str:
    """
    Escapes characters for MarkdownV2.
    
    Parameters
    ----------
    text: str
        The text to escape.

    Returns
    -------
        Return the escaped text.
    """
    escape_chars = '_*[]()~`>#+-=|{}.!'
    return ''.join(['\\' + char if char in escape_chars else char for char in text])

def parse_message(message) -> str:
    """
    Parse a NTFY message event into a string that can be send to telegram.
    Note: this method expects a NTFY message where the event field is message.
    Any other event types are not considered and lead to a bad string.

    Parameters
    ----------
    message
        The json message from NTFY.

    Returns
    -------
    text_content: str
        Return the message as a string ready for telegram.
    """
    # parse the fields from the message
    # TODO: Manage actions and attachments
    current_topic = message.get('topic')
    title = message.get('title')
    body = message.get('message')
    tags = message.get('tags',[])
    priority = message.get('priority',3)
    click = message.get('click')
    actions = message.get('actions')
    attachment = message.get('attachment')
    
    # check if content is formatted using markdown
    isMarkdown = False
    if 'content_type' in message and message['content_type'] == 'text/markdown':
        isMarkdown = True
    
    # prepare full text for telegram
    text_content = ""
    non_emoji_tags=[]

    # append topic name to the message
    if env.ntfy_include_topic == "True":
        if current_topic is not None:
            text_content += f"{current_topic}\n"
    
    # convert tags to emojis
    if len(tags) != 0:
        hasEmojis = False
        for tag in tags:
            if tag in emoji_map:
                hasEmojis = True
                text_content += emoji_map[tag]
            else:
                non_emoji_tags.append(tag)
        # add space after emojis
        if hasEmojis:
            text_content += " "
    
    # append title
    if title is not None:
        text_content += f"{title} "

    # convert priority to icon
    if env.ntfy_include_priority == "True":
        text_content += priority_emoji[priority-1]
    
    # append new line after title
    if (title is not None) or ((env.ntfy_include_priority == "True") and (priority != 3)):
        text_content += "\n\n"

    # if the message has markdown text we convert it into telegram 
    # compatible MarkdownV2, otherwise we can send the text directly,
    # but first we need to escape eventual markdown characters from it
    # or telegram will complain.
    if isMarkdown:
        text_content += escape(body)
    else:
        text_content += escape_markdown_v2(body)
    
    # add remaining non emoji tags
    if len(non_emoji_tags) != 0:
        text_content += f"\ntags: {','.join(non_emoji_tags)}"

    # add click action
    if click is not None:
        text_content += f"\n[{escape_markdown_v2(click)}]({click})"
    
    logger.debug(f"{text_content=}")
    return text_content

def telegram_send_message(message: str):
    """
    Send a massage to telegram using the bot.
    The message should be formatted for telegram to be sent using MarkdownV2.

    Parameters
    ----------
    message: str
        Message to send correctly formatted for telegram
    """
    headers = {
        "content-type": "application/x-www-form-urlencoded"
    }
    querystring = {
        "chat_id": env.tg_chat_id,
        "text": message,
        "parse_mode": "MarkdownV2", # Enable Markdown v2 formatting
        "link_preview_options": "{\"is_disabled\": true}" # Disable link preview
    }
    response = requests.request(
        "POST", 
        f"https://api.telegram.org/bot{env.tg_token}/sendMessage",
        headers=headers, 
        params=querystring
    )

    if response.ok:
        logger.info("message sent successfully")
    else:
        logger.error(f"error sending message: {response.status_code} {response.reason}")

######################
# websockets callbacks
######################
def ws_on_message(ws, message):
    message = json.loads(message)

    # if message is missing event filed it is considered invalid
    if 'event' not in message:
        logger.warning(f"got message without event field: {message}")
        return

    # skip all events where type is not message
    if message['event'] != 'message':
        logger.debug(f"skip message event of type '{message['event']}'")
        return

    if 'topic' not in message:
        logger.warning(f"got message without a valid topic: {message}")
        return

    logger.info(f"received new message from topic '{message['topic']}'")
    tg_msg = parse_message(message)
    telegram_send_message(tg_msg)

def ws_on_error(ws, error):
    logger.error(f"websocket error: {error.__repr__()}")

def ws_on_close(ws, close_status_code, close_msg):
    msg = f"websocket connection to {env.get_ws_address()} closed"
    if close_status_code is not None:
        msg += f" {close_status_code} {close_msg}"
    logger.info(msg)

def ws_on_open(ws):
    logger.info(f"websocket connection to {env.get_ws_address()} opened!")
    logger.info(f"listening to topics: {env.topic_list()}")

##########################
# websocket util functions
##########################
def get_auth_header() -> str|None:
    """
    Compute the Authorization header for the websocket connection.

    The Authorization header is set when either a token or a username/password
    are provided. If the user provides a username/password the authentication 
    string must be a base64 encoded colon-separated <username>:<password>. 
    To avoid passing plain credentials in the environment the user can generate 
    the code by himself and pass it to NTFY_PASSWORD without setting NTFY_USERNAME.
    
    Returns
    -------
    str|None
        Return a string with the value of the authorization header or None if no 
        authorization is needed.
    """
    
    if env.ntfy_token is not None:
        # use token
        return f"Bearer {env.ntfy_token}"
    elif env.ntfy_password is not None:
        # use password encoded
        basic = env.ntfy_password
        if env.ntfy_username is not None:
            # encode username and password
            basic = base64.b64encode(
                f"{env.ntfy_username}:{env.ntfy_password}".encode('ascii')
            ).decode('ascii')
        return f"Basic {basic}"
    # no auth
    return None

###############
# main function
###############
if __name__ == "__main__":
    # create app context
    env = Env()
    env.load_from_env()

    # set log level
    logger.setLevel(env.log_level)

    # create websocket headers
    header = {}
    auth_header = get_auth_header()
    if auth_header is not None:
        header['Authorization'] = auth_header

    # connect websocket
    logger.info(f"connecting to '{env.get_ws_address()}'")
    # websocket.enableTrace(True)
    websocket.setdefaulttimeout(5)
    ws_app = websocket.WebSocketApp(
        env.get_ws_address(),
        on_open=ws_on_open,
        on_message=ws_on_message,
        on_error=ws_on_error,
        on_close=ws_on_close,
        header=header
    )
    ws_app.run_forever()
