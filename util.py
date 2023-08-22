# tools and tricks for working with weather feeds
import deepl

from pathlib import Path
import re
import shutil
import json
import os
from smtplib import SMTP
from email.message import EmailMessage

import logging
logger = logging.getLogger('util')

try:
    TRANSLATOR = deepl.Translator(os.environ['DEEPL_API_KEY'])
except KeyError:
    logger.warning("Missing DEEPL_API_KEY env variable. Translations will be a no-op")
    TRANSLATOR = None

def sendEmail(recipients, subject, body , url=None):
    if recipients is not None:
        SMTP_SERVER = "email-smtp.us-east-2.amazonaws.com"
        SMTP_USERNAME = os.environ['SMTP_USERNAME']
        SMTP_PASSWORD = os.environ['SMTP_PASSWORD']
        SENDER_EMAIL = 'Automated Message Sender <knightlab@northwestern.edu>'

        msg = EmailMessage()
        msg['From'] = SENDER_EMAIL
        msg['To'] = recipients
        msg['Subject'] = subject
        if url:
            body = body + "\n\n" + "el articulo se puede encontrar en " + url
        msg.set_content(body)

        with SMTP(SMTP_SERVER) as smtp:
            smtp.starttls()
            smtp.login(SMTP_USERNAME, SMTP_PASSWORD)
            smtp.send_message(msg)
    else:
        logger.debug(f"sendEmail but No recipients")
        logger.debug(f"subject: {subject}")
        logger.debug(body)
        logger.debug('-------')

# Function to load previously parsed IDs from the 'parsed_ids.txt' file
def contains_area(in_string, arealist):
    for substring in arealist:
        if substring.casefold() in in_string.casefold():
            return True
    return False

def load_parsed_data(filepath):
    parsed_data = {}
    if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
        try:
            with open(filepath, "r") as file:
                parsed_data = json.load(file)
        except json.JSONDecodeError:
            # Handle JSONDecodeError (invalid JSON file)
            pass
    return parsed_data

# Function to save the updated parsed IDs and their corresponding file contents to JSON
def save_parsed_data(parsed_data,filepath):
    with open(filepath, "w") as file:
        json.dump(parsed_data, file)

def translate(lines):
    if TRANSLATOR:
        text_for_translation = lines

        result = TRANSLATOR.translate_text(
            text_for_translation,
            source_lang="EN",
            target_lang="ES",
            formality="prefer_more",
            split_sentences="nonewlines",
            preserve_formatting=True ) # Corrected to a boolean value
        
        return result.text
    return lines

def walk_storms (dir) : 
    for file in dir.glob("*.txt"):
        yield file
    for file in dir.glob("*"):
        if file.is_dir():
            for f in walk_storms(file):
                yield f

def walk_notices(root_dir_path):
    """a generator which yields all .txt files in the given path, or below it."""
    if type(root_dir_path) != Path:
        root_dir_path = Path(root_dir_path)
    for d in root_dir_path.glob('*'):
        if d.is_dir():
            for f in walk_storms(d):
                yield f
        elif d.is_file() and d.name.endswith('.txt') or d.name.endswith('.json') or d.name.endswith('.xml'):
            yield(d)




 
HEADLINE_PAT = re.compile('^\.\.\.(.+)\.\.\.$')
def get_headlines(txt_lines):
    """Given a pre-split array of lines from a notice,
       return an array of the "headlines" found within.
    """
    headlines = []
    in_hed = False
    partials = []
    for line in txt_lines:
        if line.startswith('...'):
            line = line[3:]
            if line.endswith('...'):
                line = line[:-3]
                headlines.append(line)
            else:
                partials.append(line)
                in_hed = True
        elif in_hed and line.endswith('...'):
            line = line[:-3]
            partials.append(line)
            headlines.append(' '.join(partials))
            partials = []
            in_hed = False
        elif in_hed:
            partials.append(line)
    if partials: # hasn't happened yet, probably won't
        print('unresolved partials')
        print(partials)
                
    return headlines


def initialize_directory(directory):
    """given a path, make sure it's an empty directory. That is, create it if necessary, 
    and clean out anything that might have been in it"""
    # TODO: refactor cleanup into a separate method for readability
    os.makedirs(directory, exist_ok=True)
    for file in os.listdir(directory):
        file_path = os.path.join(directory, file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            logging.warning("Error while deleting:", e)
