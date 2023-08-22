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

from NWS import  fetch_nws_data, writeNWS
from NHC import writeNHC
from blox import make_cms_link, post_story
from util import sendEmail, initialize_directory

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

    
def main_nws(testfile=None):
    nwsjson_directory = "bulletins/NWSjson"
    initialize_directory(nwsjson_directory)

    if testfile:
        logger.debug(f"NWS using test file {testfile}")
        nws_json = json.load(testfile)
    else:
        nws_json = fetch_nws_data()


    # TODO: support passing in a file via command line for testing
    nws_json = fetch_nws_data()
    if nws_json: # TODO pass JSON instead of file
        textid= datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        filelocation=os.path.join(nwsjson_directory,f"{textid}.json")
        with open(filelocation,"w") as file:
            json.dump(nws_json, file)

    # TODO: pass JSON instead of file
    generated = writeNWS(filelocation)

    with open("nws_generated.json", 'w') as f: # temporary
        json.dump(generated, f, indent=2)
        logger.debug("wrote nws_generated.json")

    for story in generated:
        post_story(story["headline"], story["content"] , story.get('image_code'))

def main_nhc(testfile=None):
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

    if testfile:
        writeNHC(testfile)
    else:
        for url in nhc_urls:
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
                    return
                print (parsed)
                content = parsed["content"]  
                if parsed["action"] == "email": 
                    logger.info(f"Email subject: {content['headline']}")
                    logger.debug(content['body'])
                    if email_recipients:
                        sendEmail(email_recipients, content["headline"], content["body"])
                    else:
                        logger.warning("Email action with no recipients configured")
                elif parsed["action"] == "post":       
                    for event in content: # TODO make sure image_codes are set correctly
                        story_id = post_story(event["headline"], event["body"] , event.get('image_code'))
                        url = make_cms_link(story_id)

                        sendEmail(email_recipients, event["headline"], event["email"] , url)

            else:
                logger.warning(f"Failed to retrieve NHC API data. Status code {response.status_code}")

            

# Main script
def main(test_mode=False, nws_testfile=None, nhc_testfile=None):
    configure_logging(logger)

    logger.info("Weatherbot begin")
    if test_mode:
        logger.debug('test mode')
        if nws_testfile:
            main_nws(nws_testfile)
        else:
            logger.debug("No NWS test file, skipping")
        if nhc_testfile:
            main_nhc(nhc_testfile)
        else:
            logger.debug("No NHC test file, skipping")
    else:
        main_nws()
        main_nhc()

    logger.info("Weatherbot complete")


   
if __name__ == "__main__":
    """Usage: python main.py [--nws path_to_nws_test_json] [--nhc path_to_nhc_test_xml]

        if run with no flags, this system will fetch and analyze the data from the NWS and NHC. 
        As appropriate, the system will cause a story to be posted to El Vocero's CMS and/or send email.

        NOTE: When run in "test mode," the system will still publish to the CMS. If the post has no 
        start_time, it will be automatically live. TODO: consider future dating test posts, or doing something
        other than posting, or making that another command line flags?
    
    """
    import argparse
    parser = argparse.ArgumentParser(description='Check weather services and post stories as relevant.')
    parser.add_argument('--nws', nargs="?", type=argparse.FileType('r'))
    parser.add_argument('--nhc', nargs="?", type=argparse.FileType('r'))
    args = parser.parse_args()
    test_mode = args.nhc or args.nws
    print(args)
    main(test_mode, nws_testfile=args.nws, nhc_testfile=args.nhc)
