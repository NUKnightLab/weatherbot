#!/usr/bin/env python
#
# When executed, this script checks data feeds from the 
# National Weather Service and the National Hurricane Center
# Feed data is evaluated based on rules provided by El Vocero
# When relevant, an HTML fragment "story" is generated based on the 
# data and posted to El Vocero's CMS.
# If a story is posted, an email is also sent to notify interested parties.
#
# TODO: all time shuld be UTC-4 -- not AST
#       take that out of headlines especially
# TODO: get glossary

import requests
import datetime
from io import StringIO
import os
import json

from NWS import  fetch_nws_data, generate_nws_stories
from NHC import writeNHC
from blox import make_cms_link, post_story
from util import send_email, initialize_directory

import logging
from logging.handlers import TimedRotatingFileHandler

logger = logging.getLogger()

# else:
#     print("Failed to retrieve API data. Status code:", response.status_code)

def configure_logging(logger):
    loglevel = os.environ.get('LOGLEVEL', 'INFO')
    logging.basicConfig(
        format='%(name)s - %(levelname)s - %(message)s',
        level=loglevel
    )

    logfile_path = os.environ.get('LOGFILE')
    if logfile_path:
        # daily log files for one week
        handler = TimedRotatingFileHandler(logfile_path, when='d', interval=1, backupCount=6)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(handler)

    # usually we want to hush these. Comment out if you like.
    deepl_logger = logging.getLogger('deepl')
    deepl_logger.setLevel(logging.WARNING) # chatty at INFO

    urllib3_logger = logging.getLogger('urllib3.connectionpool')
    urllib3_logger.setLevel(logging.INFO) # chatty at DEBUG

    
def main_nws(testfile=None, actually_post_articles=False):
    nwsjson_directory = "bulletins/NWSjson"
    initialize_directory(nwsjson_directory)

    if testfile:
        logger.debug(f"NWS using test file {testfile.name}")
        nws_json = json.load(testfile)
    else:
        nws_json = fetch_nws_data()

    if nws_json:
        textid= datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        filelocation=os.path.join(nwsjson_directory,f"{textid}.json")
        with open(filelocation,"w") as file:
            json.dump(nws_json, file)

    # TODO: pass JSON instead of file
    generated = generate_nws_stories(filelocation)

    with open("nws_generated.json", 'w') as f: # temporary
        json.dump(generated, f, indent=2)
        logger.debug("wrote nws_generated.json")

    for story in generated:
        post_story(story["headline"], story["content"] , story.get('image_code'), actually_post_articles=actually_post_articles)

def main_nhc(testfile=None, actually_send_email=False, actually_post_articles=False):
    email_recipients = os.environ.get('EMAIL_RECIPIENTS')
    if email_recipients:
        email_recipients = email_recipients.split(',')
        logger.info(f"Email notification set to {email_recipients}")
    else:
        logger.warning("No email notification recipients set")



    tcpat_directory = "bulletins/TCPAT"
    initialize_directory(tcpat_directory)


    ###NHC PRODUCTS
    nhc_urls=[
        "https://www.nhc.noaa.gov/xml/TCPAT1.xml", 
        "https://www.nhc.noaa.gov/xml/TCPAT2.xml",
        "https://www.nhc.noaa.gov/xml/TCPAT3.xml", 
        "https://www.nhc.noaa.gov/xml/TCPAT4.xml",
        "https://www.nhc.noaa.gov/xml/TCPAT5.xml"
    ]

    results = []

    if testfile:
        try:
            results.append(writeNHC(testfile))
        except ValueError as e: # we don't need stack trace for this. This seems overly complex tho, should be able to trap better
            logger.error(f"Error processing bulletin {testfile} {e}")
        except Exception as e:
            logger.error(f"Error processing bulletin {testfile} {e}")
            logger.exception(e)
    else:
        for url in nhc_urls:
            try:
                wallet = url.split("xml/")[1].split(".xml")[0]
                response = requests.get(url)
                if response.status_code == 200:
                    textid = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                    response.encoding = 'utf-8'
                    
                    filelocation = os.path.join(tcpat_directory, f"{wallet}_{textid}.xml")
                    
                    with open(filelocation, "w") as file:
                        file.write(response.text) 
                    parsed = writeNHC(StringIO(response.text)) 
                    if parsed== {}:
                        pass # TODO: this was "return" which would skip any URLs after this case. Make sure there wasn't a reason for it.
                    else:
                        results.append(parsed)
                else:
                    logger.warning(f"Failed to retrieve NHC API data. Status code {response.status_code}")
            # except ValueError as e: # we don't need stack trace for this. This seems overly complex tho, should be able to trap better
            #     logger.error(f"Error processing bulletin {url} {e}")
            except Exception as e:
                logger.error(f"Error processing bulletin {url} {e}")
                logger.exception(e)

    if results:
        for parsed in results:
            content = parsed.get("content")
            if content:
                if parsed["action"] == "email": 
                    if email_recipients:
                        send_email(email_recipients, content["headline"], content["body"], actually_send_email=actually_send_email)
                    else:
                        logger.warning("Email action with no recipients configured")
                elif parsed["action"] == "post":       
                    for event in content: # TODO make sure image_codes are set correctly
                        story_id = post_story(event["headline"], event["body"] , event.get('image_code'), actually_post_articles=actually_post_articles)
                        url = make_cms_link(story_id)
                        send_email(email_recipients, event["headline"], event["email"] , url, actually_send_email=actually_send_email)

# Main script
def main(test_mode=False, actually_send_email=False, actually_post_articles=False, nws_testfile=None, nhc_testfile=None):
    configure_logging(logger)

    runtime_marker = datetime.datetime.now().strftime('%Y-%m-%d_%H:%M')
    logger.info(f"------- Weatherbot begin {runtime_marker}")

    if not actually_post_articles:
        logger.info("Post articles flag is not set. No articles will be posted")
    if not actually_send_email:
        logger.info("Send email flag is not set. No email will be sent")
        
    if test_mode:
        logger.debug('test mode')

        if nws_testfile:
            main_nws(testfile=nws_testfile,  actually_post_articles=actually_post_articles)
        else:
            logger.debug("No NWS test file, skipping")

        if nhc_testfile:
            main_nhc(nhc_testfile, actually_send_email=actually_send_email, actually_post_articles=actually_post_articles)
        else:
            logger.debug("No NHC test file, skipping")
    else:

        try:
            main_nws(actually_post_articles=actually_post_articles)
        except Exception as e:
            logger.error(f"Uncaught exception in main_nws: {e}")
            logger.exception(e)

        try:
            main_nhc(actually_send_email=actually_send_email, actually_post_articles=actually_post_articles)
        except Exception as e:
            logger.error(f"Uncaught exception in main_nhc: {e}")
            logger.exception(e)

    logger.info(f"------- Weatherbot complete {runtime_marker}")


   
if __name__ == "__main__":
    """Usage: python main.py [--post|-p] [--email|-e] [--nws path_to_nws_test_json] [--nhc path_to_nhc_test_xml] 

        When run, call data services for NWS and NHC, preparing data for posting to a CMS and 
        sending via email notifications. Both posting and email REQUIRE explicit flags; if not set,
        details of what would have been posted/emailed will be logged instead.

        
    """
    import argparse
    parser = argparse.ArgumentParser(description='Check weather services and post stories as relevant.')
    parser.add_argument('--nws', nargs="?", type=argparse.FileType('r'))
    parser.add_argument('--nhc', nargs="?", type=argparse.FileType('r'))
    parser.add_argument('-p', '--post', help="Post articles to CMS", action="store_true")
    parser.add_argument('-e', '--email', help="Send emails", action="store_true")

    args = parser.parse_args()
    test_mode = args.nhc or args.nws

    main(test_mode, actually_send_email=args.email, actually_post_articles=args.post, nws_testfile=args.nws, nhc_testfile=args.nhc)
