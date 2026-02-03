import random
import logging
from fastapi import FastAPI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

app = FastAPI()

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


# API endpoints
@app.get("/message/{locale}")
@app.get("/message/")
def message(locale: str = "en"):
    return {"message": getRandomMessage(locale)}
