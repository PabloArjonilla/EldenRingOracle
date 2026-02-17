from flask import Flask, request
import random
import logging
import os

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# Get the directory where this script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Loading all messages
logger.info("Loading messages from all available languages...")
supported_languages = []
supported_languages_hashtags = []
messages_by_language = {}

# FIXED: Proper file path construction and error handling
try:
    categories_file = os.path.join(BASE_DIR, "Messages", "Categories")  # Fixed the path
    with open(categories_file, 'r') as f:
        messages_word_categories = f.read().splitlines()
    logger.info(f"Loaded {len(messages_word_categories)} categories")
except FileNotFoundError:
    logger.error(f"Categories file not found at {categories_file}")
    messages_word_categories = []

try:
    locales_file = os.path.join(BASE_DIR, "Messages", "Locales")  # Fixed the path
    with open(locales_file, 'r') as f:
        locales_content = f.read().splitlines()
    logger.info(f"Loaded {len(locales_content)} locales")
except FileNotFoundError:
    logger.error(f"Locales file not found at {locales_file}")
    locales_content = ['en']  # Default to English

for language in locales_content:
    supported_languages.append(language)
    supported_languages_hashtags.append(f"#{language}")
    try:
        language_messages = {}

        # FIXED: Proper file paths
        conjunctions_file = os.path.join(BASE_DIR, "Messages", language, "Conjunctions")
        templates_file = os.path.join(BASE_DIR, "Messages", language, "Templates")

        with open(conjunctions_file, 'r') as f:
            language_conjunctions = f.read().splitlines()

        with open(templates_file, 'r') as f:
            language_templates = f.read().splitlines()

        language_words_by_category = {}
        for category in messages_word_categories:
            word_file = os.path.join(BASE_DIR, "Messages", language, "Words", category)
            try:
                with open(word_file, 'r') as f:
                    language_words_by_category[category] = f.read().splitlines()
            except FileNotFoundError:
                logger.warning(f"Word file not found: {word_file}")
                language_words_by_category[category] = []

        language_messages["conjunctions"] = language_conjunctions
        language_messages["templates"] = language_templates
        language_messages["words_by_category"] = language_words_by_category
        messages_by_language[language] = language_messages

        logger.info(f"Loaded language: {language}")

    except FileNotFoundError as e:
        logger.error(f"Locale {language} not found: {e}")

# Message functions
def getRandomPhrase(locale):
    if locale not in messages_by_language:
        locale = "en"  # Fallback to English

    if not messages_by_language[locale]["templates"]:
        return "No templates available"

    random_template = random.choice(messages_by_language[locale]["templates"])

    # Better category selection with fallback
    available_categories = [cat for cat in messages_word_categories if cat in messages_by_language[locale]["words_by_category"] and messages_by_language[locale]["words_by_category"][cat]]

    if not available_categories:
        return random_template.replace("*", "word")

    random_category = random.choice(available_categories)
    random_word = random.choice(messages_by_language[locale]["words_by_category"][random_category])

    return random_template.replace("*", random_word)

def getRandomConjunction(locale):
    if locale not in messages_by_language or not messages_by_language[locale]["conjunctions"]:
        return getRandomPhrase(locale)  # Fallback if no conjunctions

    random_conjunction = random.choice(messages_by_language[locale]["conjunctions"])
    return getRandomPhrase(locale) + " " + random_conjunction + " " + getRandomPhrase(locale)

def getRandomMessage(locale):
    if locale is None or locale not in messages_by_language:
        locale = "en"

    if bool(random.getrandbits(1)):
        return getRandomPhrase(locale)
    else:
        return getRandomConjunction(locale)


@app.route("/scramble", methods=["POST"])
def scramble():
    data = request.get_json()
    if not data or "message" not in data:
        return {"error": "JSON body with 'message' field is required"}, 400

    message = data["message"]
    words = message.split()
    punctuation = {}
    stripped_words = []
    for i, word in enumerate(words):
        trailing = ""
        while word and not word[-1].isalnum():
            trailing = word[-1] + trailing
            word = word[:-1]
        if trailing:
            punctuation[i] = trailing
        stripped_words.append(word)

    random.shuffle(stripped_words)

    result = []
    for i, word in enumerate(stripped_words):
        if i in punctuation:
            word += punctuation[i]
        result.append(word)

    return {"message": " ".join(result)}


@app.route("/message/<locale>")
@app.route("/message/")
def message(locale="en"):
    try:
        return {"message": getRandomMessage(locale)}
    except Exception as e:
        logger.error(f"Error generating message: {e}")
        return {"error": "Failed to generate message"}, 500

@app.route("/")
def index():
    return {"status": "EldenRingOracle API is running", "endpoint": "/message/<locale>"}

if __name__ == "__main__":
    app.run(debug=True)