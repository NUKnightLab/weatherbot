import deepl

from pathlib import Path
import re
import shutil
import json
import os
from smtplib import SMTP
from email.message import EmailMessage
import time
from jinja2 import Environment, FileSystemLoader, select_autoescape

from datetime import datetime, timedelta
import logging
logger = logging.getLogger('util')

SMTP_SERVER = "email-smtp.us-east-2.amazonaws.com"
SENDER_EMAIL = 'Weatherbot <knightlab@northwestern.edu>'

JINJA_ENVIRONMENT = Environment(
    loader=FileSystemLoader('templates'),
    autoescape=select_autoescape()
)


def render_template(path, **kwargs):
    """Given a relative template path and any context for rendering the template,
    do it all here, in one place. """
    template = JINJA_ENVIRONMENT.get_template(path)
    return template.render(**kwargs)

def send_email(recipients, subject, body , url=None, actually_send_email=False):
    try:
        SMTP_USERNAME = os.environ['SMTP_USERNAME']
        SMTP_PASSWORD = os.environ['SMTP_PASSWORD']
    except KeyError:
        if actually_send_email:
            logger.warn("Email configuration error: SMTP_USERNAME and SMTP_PASSWORD must be set as environment variables. Email will not be sent.")
        actually_send_email = False        


    if recipients is not None:
        msg = EmailMessage()
        msg['From'] = SENDER_EMAIL
        msg['To'] = recipients
        msg['Subject'] = subject
        if url:
            body = body + "\n\n" + "el articulo se puede encontrar en " + url
        msg.set_content("This is a fallback plain text message")
        msg.add_alternative(body, subtype='html')

        if actually_send_email:
            logger.info(f"send_email [{subject}] to [{recipients}]")
            with SMTP(SMTP_SERVER) as smtp:
                smtp.starttls()
                smtp.login(SMTP_USERNAME, SMTP_PASSWORD)
                smtp.send_message(msg)
        else:
            logger.info("Email send not enabled. Details at debug")
            logger.debug(f"To: {recipients}")
            logger.debug(f"From: {SENDER_EMAIL}")
            logger.debug(f"Body:")
            logger.debug(body)
            logger.debug('---------')
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

def load_parsed_data(filepath: str) -> dict:
    parsed_data = {}
    if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
        try:
            with open(filepath, "r") as file:
                parsed_data = json.load(file)
            if type(parsed_data) != dict: # typing should maybe make this irrelevant?
                logger.warning(f"Loaded {filepath} but got a non-dict {parsed_ids}")
                parsed_ids = {}

        except json.JSONDecodeError:
            # Handle JSONDecodeError (invalid JSON file)
            pass
    return parsed_data

# Function to save the updated parsed IDs and their corresponding file contents to JSON
def save_parsed_data(parsed_data: dict, filepath: str):
    with open(filepath, "w") as file:
        json.dump(parsed_data, file)

class Translator(object):
    """A callable which manages translation with DeepL, if its configured, or just passes text through otherwise"""
    auth_ok = False
    translator = None
    logger = logging.getLogger('Translator')
    glossary_id = None
    def __init__(self) -> None:
        api_key = os.environ.get('DEEPL_AUTH_KEY')
        if api_key:
            self.translator = deepl.Translator(api_key)
            self.auth_ok = True
            self.glossary_id = os.environ.get('DEEPL_GLOSSARY_ID', None)

        else:
            self.logger.warning("Missing DEEPL_AUTH_KEY env variable. Translations will be a no-op")

    def __call__(self, lines: str) -> str:
        if self.translator and self.auth_ok:
            try:
                kwargs = {
                    'source_lang': "EN",
                    'target_lang': "ES",
                    'formality': "prefer_more",
                    'split_sentences': "nonewlines",
                    'preserve_formatting': True
                }
                if self.glossary_id:
                    kwargs['glossary'] = self.glossary_id

                result = self.translator.translate_text(lines, **kwargs)
                return result.text
            except Exception as e:
                self.logger.error(f"Error using translation: {e}")
                # TODO maybe send email?
                self.auth_ok = False
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

def is_too_old(file_path, age_in_seconds):
    if age_in_seconds is None:
        return False
    return ( time.time() - os.path.getmtime(file_path) ) > age_in_seconds

def initialize_directory(directory, maxage=604800):
    """given a path, make sure it's an empty directory. That is, create it if necessary. 
    Then clean out any files older than maxage (in seconds). if maxage is None, no files will be deleted. 
    if maxage is 0, all files will be deleted."""
    os.makedirs(directory, exist_ok=True)
    for file in os.listdir(directory):
        file_path = os.path.join(directory, file)
        try:
            if os.path.isfile(file_path) and is_too_old(file_path, maxage):
                os.unlink(file_path)
            # for now skip trying to figure out if directories are empty, it's no big deal to keep empty dirs around.
            # elif os.path.isdir(file_path):
            #     shutil.rmtree(file_path)
        except Exception as e:
            logging.warning("Error while deleting:", e)

def convert_time(date_string, format):
    try:
        if format == "NHC":
            date_obj = datetime.strptime(date_string, "%a, %d %b %Y %H:%M:%S %z")
            gmt_minus_4 = timedelta(hours=4)
            date_gmt_minus_4 = date_obj - gmt_minus_4
        elif format == "NWS":
            date_obj = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S%z")
            date_gmt_minus_4 = date_obj
        else:
            logger.error("Invalid format_flag")
            return date_string

        # Round minutes and seconds to the nearest hour
        if date_gmt_minus_4.minute >= 30:
            date_gmt_minus_4 = date_gmt_minus_4.replace(minute=0, second=0) + timedelta(hours=1)
        else:
            date_gmt_minus_4 = date_gmt_minus_4.replace(minute=0, second=0)

        # Format the time in 12-hour format with AM/PM
        formatted_time_string = date_gmt_minus_4.strftime("%I:%M %p")

        # Format the date in the "Month day" format
        formatted_date_string = date_gmt_minus_4.strftime("%B %d")

        return f"{formatted_date_string} at {formatted_time_string}"
    except ValueError:
        logger.error("Invalid date string format")
        return date_string
def headline_to_gmt_minus_4(headline,published,expires):
    date_time_pattern = r"(\w+\s+\d+ at \d+:\d+\w{2}) ([A-Z]+)"
    issued = ""
    until = ""
    matches = re.findall(date_time_pattern, headline)
    for i in range(len(matches)):
        if i == 0:
            issued = matches[i][0]+ " " + matches[i][1]
        else :
            until = matches[i][0]+ " " + matches[i][1]
    new_headline = headline.replace("issued " + issued, "issued " + published).replace("until " + until, "until " + expires)
    return new_headline
# # Example usage:
# date_string1 = "Mon, 28 Aug 2023 14:59:27 +0000"
# date_string2 = "2023-09-08T15:50:00-04:00"

# formatted_time1 = convert_time(date_string1, format="NHC")
# formatted_time2 = convert_time(date_string2, format="NWS")

# print(formatted_time1)
# print(formatted_time2)
