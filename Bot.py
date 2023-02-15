import configparser
import random
import logging
import time
import tweepy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()


# Getting API keys and TOKENS
logger.info("Loading keys...")
keys = open('Passwords', 'r').read().splitlines()
api_key = keys[0]
api_key_secret = keys[1]
access_token = keys[2]
access_token_secret = keys[3]

# Loading all messages
logger.info("Loading messages from all available languages...")

supported_languages = []
supported_languages_hashtags = []

messages_by_language = {}
messages_word_categories = open(f"Messages/Categories", 'r').read().splitlines()

for language in open(f"Messages/Locales", 'r').read().splitlines():
    supported_languages.append(language)
    supported_languages_hashtags.append(f"{language}")

    try:
        language_messages = {}
        language_conjunctions = open(f"Messages/{language}/Conjunctions", 'r').read().splitlines()
        language_templates = open(f"Messages/{language}/Templates", 'r').read().splitlines()
        language_words_by_category = {}

        for category in messages_word_categories:
            language_words_by_category[category] = open(f"Messages/{language}/Words/{category}", 'r').read().splitlines()

        language_messages["conjunctions"] = language_conjunctions
        language_messages["templates"] = language_templates
        language_messages["words_by_category"] = language_words_by_category

        messages_by_language[language] = language_messages

    except FileNotFoundError as e:
        logger.error(f"Locale {language} not found.")


# Message functions

def getRandomPhrase(locale):
    random_template = random.choice(messages_by_language[locale]["templates"])
    random_word = random.choice(messages_by_language[locale]["words_by_category"][random.choice(messages_word_categories)])
    return random_template.replace("*", random_word)


def getRandomConjunction(locale):
    random_conjunction = random.choice(messages_by_language[locale]["conjunctions"])
    return getRandomPhrase(locale) + random_conjunction + getRandomPhrase(locale)


def getRandomMessage(locale):

    if locale == None:
        locale = "en"

    if bool(random.getrandbits(1)):
        return getRandomPhrase(locale)
    else:
        return getRandomConjunction(locale)


# API functions

def create_api():
    authenticator = tweepy.OAuthHandler(api_key, api_key_secret)
    authenticator.set_access_token(access_token, access_token_secret)
    api = tweepy.API(authenticator, wait_on_rate_limit=True)
    try:
        api.verify_credentials()
    except Exception as e:
        logger.error("Error creating API", exc_info=True)
        raise e
    logger.info("API created")
    return api

pending_responses = []

def check_mentions(api):
    logger.info("Retrieving mentions")

    mentionCursor = int(open('mentionsCursor','r').read())

    for tweet in tweepy.Cursor(api.mentions_timeline,
                               since_id=mentionCursor).items():
        mentionCursor = max(tweet.id, mentionCursor)
        
        messageRequested = False
        language = "en"
        for hashtag in tweet.entities['hashtags']:
            hashtag  = hashtag["text"]
            if hashtag == "message":
                messageRequested = True
            if hashtag in supported_languages_hashtags:
                language = hashtag
                

        if messageRequested:
            logger.info(f"{tweet.user.name} requested a {language} message...")
            replyTweet = str(f"@{tweet.user.screen_name} {getRandomMessage(language)}")
            logger.info(replyTweet)
            api.update_status(status=replyTweet,in_reply_to_status_id=tweet.id,)

    open('mentionsCursor','w').write(str(mentionCursor))

# APP
def main():
    api = create_api()
    
    while True:
        check_mentions(api)
        logger.info("Waiting...")
        time.sleep(30)

if __name__ == "__main__":
    main()
