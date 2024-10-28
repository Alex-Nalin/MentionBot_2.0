# Mention Bot 2.0

Symphony Room @mention bot by Alex Nalin (Symphony Lead Solutions Architect)

This bot was build using the Symphony Python BDK. (QAed: 2.6.0)

https://developers.symphony.com/symphony-developer/docs/get-started-with-python.


<b>WORKFLOW</b>

Add bot to room and use @mention /all to @mention all members of the stream (Room/MIM/IM)

##

- Commands list:

    @Mention Bot /help
    
    @Mention Bot /all


##

- <b>Bot Deployment</b>:

Create a Symphony Service Account on your private pod:
https://developers.symphony.com/symphony-developer/docs/create-a-bot-user

Generate an RSA Key Pair:

    openssl genrsa -out mykey.pem 4096
    openssl rsa -in mykey.pem -pubout -out pubkey.pem

Copy (zip) or clone this Mention Bot's latest code from this repo:
https://github.com/Alex-Nalin/MentionBot_2.0

Install the required libraries:

    pip install -r requirements.txt

Modify resources\config.yaml to point to your desired Pod and update the below info about your bot:

    host: <yourpodname>.symphony.com
    
    bot:
      username: MentionBot
      id: <botuserid>
      privateKey:
        path: rsa/privatekey.pem
    bot_audit: <streamid of a room with the bot for audit tracking>
    
Modify the config.yaml to add your Company name (as visible to others) under allowedPod:

    "allowedPod" : "Symphony Private Pod Name",
    
You can decide to log to STDERR (useful for docker) or to a log file by updating resources/logging.conf

STDERR:

    [loggers]
    keys=root
    
    [handlers]
    keys=consoleHandler
    
    [formatters]
    keys=simpleFormatter
    
    [logger_root]
    level=DEBUG
    handlers=consoleHandler
    
    [handler_consoleHandler]
    class=StreamHandler
    level=DEBUG
    formatter=simpleFormatter
    args=(sys.stdout,)
    
    [formatter_simpleFormatter]
    format=%(asctime)s - %(name)s - %(levelname)s - %(message)s

Log File with size rotation:

    [loggers]
    keys=root
    
    [handlers]
    keys=consoleHandler,fileHandler
    
    [formatters]
    keys=simpleFormatter
    
    [logger_root]
    level=DEBUG
    handlers=consoleHandler,fileHandler
    
    [handler_consoleHandler]
    class=StreamHandler
    level=DEBUG
    formatter=simpleFormatter
    args=(sys.stdout,)
    
    [formatter_simpleFormatter]
    format=%(asctime)s - %(name)s - %(levelname)s - %(message)s
    
    [handler_fileHandler]
    # Rotating log file if size exceeds 10MB
    class=logging.handlers.RotatingFileHandler
    level=DEBUG
    formatter=simpleFormatter
    encoding=UTF-8
    args=('log/mentionbot.log', 'w', 10000000, 50, 'utf-8')


To get started, follow these commands below:

## First run only:
1. Create virtual environment:
    - `python3 -m venv env`
2. Install dependencies:
    - `pip3 install -r requirements.txt`

## Subsequent runs:
- Activate virtual environment
    - macOS/Linux: `source env/bin/activate`
    - Windows: `env\Scripts\activate.bat`

## Run project
- `python3 -m src`