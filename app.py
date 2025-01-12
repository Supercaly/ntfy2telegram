import base64
from dotenv import dotenv_values
from emoji import rawEmojis as emoji_map
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
logger.setLevel(logging.INFO)

# get environment variables
env = {
    **dotenv_values(".env"),
    **os.environ,
}
NTFY_WS_PROTOCOL = env.get('NTFY_WS_PROTOCOL','ws')
NTFY_SERVER_ADDRESS = env.get('NTFY_SERVER_ADDRESS')
NTFY_TOPIC = env.get('NTFY_TOPIC')
NTFY_USERNAME = env.get('NTFY_USERNAME')
NTFY_PASSWORD = env.get('NTFY_PASSWORD')
NTFY_TOKEN = env.get('NTFY_TOKEN')
TG_CHAT_ID = env.get('TG_CHAT_ID')
TG_BOT_TOKEN = env.get('TG_BOT_TOKEN')

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
    
    # convert tags to emojis
    # TODO: Display priority in the title
    # TODO: Manage actions and attachments
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
        text_content += f"{title}\n\n"
    
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
        "chat_id": TG_CHAT_ID,
        "text": message,
        "parse_mode": "MarkdownV2", # Enable Markdown v2 formatting
        "link_preview_options": "{\"is_disabled\": true}" # Disable link preview
    }
    response = requests.request(
        "POST", 
        f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage", 
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
    
    logger.info("received new message from NTFY")
    tg_msg = parse_message(message)
    telegram_send_message(tg_msg)

def ws_on_error(ws, error):
    logger.error(f"websocket error: {error.__repr__()}")

def ws_on_close(ws, close_status_code, close_msg):
    msg = f"websocket connection to {get_ws_address()} closed"
    if close_status_code is not None:
        msg += f" {close_status_code} {close_msg}"
    logger.info(msg)

def ws_on_open(ws):
    logger.info(f"websocket connection to {get_ws_address()} opened!")

##########################
# websocket util functions
##########################
def get_ws_address() -> str:
    """
    Create the full address for the NTFY websocket.

    Returns
    -------
    str
        Return a string representing the full NTFY ws address.
    """
    return f"{NTFY_WS_PROTOCOL}://{NTFY_SERVER_ADDRESS}/{NTFY_TOPIC}/ws"

def validate_env():
    """
    Validate the variables read from the environment.
    """
    if NTFY_WS_PROTOCOL != "ws" and NTFY_WS_PROTOCOL != "wss":
        raise Exception(f"invalid environment variable {NTFY_WS_PROTOCOL=}")
    if NTFY_SERVER_ADDRESS is None:
        raise Exception(f"environment variable 'NTFY_SERVER_ADDRESS' is undefined") 
    if NTFY_TOPIC is None:
        raise Exception(f"environment variable 'NTFY_TOPIC' is undefined")
    if TG_CHAT_ID is None:
        raise Exception(f"environment variable 'TG_CHAT_ID' is undefined")
    if TG_BOT_TOKEN is None:
        raise Exception(f"environment variable 'TG_BOT_TOKEN' is undefined")

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
    
    if NTFY_TOKEN is not None:
        return f"Bearer {NTFY_TOKEN}"
    elif NTFY_PASSWORD is not None:
        basic = NTFY_PASSWORD
        if NTFY_USERNAME is not None:
            basic = base64.b64encode(
                f"{NTFY_USERNAME}:{NTFY_PASSWORD}".encode('ascii')
            ).decode('ascii')
        return f"Basic {basic}"
    return None

if __name__ == "__main__":
    validate_env()

    header = {}
    auth_header = get_auth_header()
    if auth_header is not None:
        header['Authorization'] = auth_header

    logger.info(f"connecting to '{get_ws_address()}'")
    # websocket.enableTrace(True)
    websocket.setdefaulttimeout(5)
    ws_app = websocket.WebSocketApp(
        get_ws_address(),
        on_open=ws_on_open,
        on_message=ws_on_message,
        on_error=ws_on_error,
        on_close=ws_on_close,
        header=header
    )
    ws_app.run_forever()
