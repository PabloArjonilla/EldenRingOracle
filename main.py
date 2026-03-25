from flask import Flask, request
import random
import logging
import os
import hmac
import hashlib
import subprocess
import zipfile
import io
import shutil
import requests

WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET")
PYTHONANYWHERE_USER = os.environ.get("USER")


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


@app.route("/git-update", methods=["POST"])
def git_update():
    # Download and extract latest code from GitHub
    zip_url = "https://github.com/PabloArjonilla/EldenRingOracle/archive/refs/heads/main.zip"
    response = requests.get(zip_url)

    z = zipfile.ZipFile(io.BytesIO(response.content))
    tmp_dir = "/tmp/repo-update"
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)
    z.extractall(tmp_dir)

    # The zip extracts to YOURREPO-main/, copy contents over
    extracted = os.path.join(tmp_dir, os.listdir(tmp_dir)[0])
    for item in os.listdir(extracted):
        src = os.path.join(extracted, item)
        dst = os.path.join(BASE_DIR, item)
        if os.path.isdir(src):
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)

    shutil.rmtree(tmp_dir)

    # Reload PythonAnywhere web app
    wsgi_file = f"/var/www/{PYTHONANYWHERE_USER}_pythonanywhere_com_wsgi.py"
    subprocess.run(["touch", wsgi_file])

    return {"status": "updated"}, 200


@app.route("/redacted", methods=["POST"])
def scramble():
    data = request.get_json()
    if not data or "message" not in data:
        return {"error": "JSON body with 'message' field is required"}, 400

    message = data["message"]
    words = message.split()

    if len(words) <= 5:
        return {"message": message}

    candidates = []
    for i, word in enumerate(words):
        stripped = word
        while stripped and not stripped[-1].isalnum():
            stripped = stripped[:-1]
        if len(stripped) > 4:
            candidates.append(i)

    guaranteed = random.choice(candidates) if candidates else None

    result = []
    for i, word in enumerate(words):
        trailing = ""
        stripped = word
        while stripped and not stripped[-1].isalnum():
            trailing = stripped[-1] + trailing
            stripped = stripped[:-1]
        if i in candidates and (i == guaranteed or random.random() < 0.6):
            result.append("[redacted]" + trailing)
        else:
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


@app.route("/version")
def version():
    return {"version": "3.0.1"}, 200


if __name__ == "__main__":
    app.run(debug=True)

