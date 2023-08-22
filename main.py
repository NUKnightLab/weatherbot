# When executed, this script checks data feeds from the 
# National Weather Service and the National Hurricane Center
# Feed data is evaluated based on rules provided by El Vocero
# When relevant, an HTML fragment "story" is generated based on the 
# data and posted to El Vocero's CMS.
# If a story is posted, an email is also sent to notify interested parties.
#
import requests
import datetime
from NWS import  fetch_nws_data, writeNWS
from NHC import writeNHC
from blox import make_cms_link, post_story
from util import sendEmail, initialize_directory
import os
import json

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

    # usually we want to hush these. it's chatty at INFO. Comment out if you like.
    deepl_logger = logging.getLogger('deepl')
    deepl_logger.setLevel(logging.WARNING) # chatty at INFO

    urllib3_logger = logging.getLogger('urllib3.connectionpool')
    urllib3_logger.setLevel(logging.INFO) # chatty at DEBUG

    
def main_nws():
    nwsjson_directory = "bulletins/NWSjson"
    initialize_directory(nwsjson_directory)

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

def main_nhc():
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


    for url in nhc_urls:
        wallet = url.split("xml/")[1].split(".xml")[0]
        response = requests.get(url)
        if response.status_code == 200:
            textid = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            response.encoding = 'utf-8'
            
            filelocation = os.path.join(tcpat_directory, f"{wallet}_{textid}.xml")
            
            with open(filelocation, "w") as file:
                file.write(response.text) 
            parsed = writeNHC('test.xml') # TODO pass test file from command line instead of editing code
            if parsed== {}:
                return
            print (parsed)
            content = parsed["content"]  
            if parsed["action"] == "email": # TODO this doesn't seem to fit any business logic
                                            # if a story is written to the CMS, an email should be sent
                                            # but the story itself isn't meant to be sent
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
def main():

    configure_logging(logger)

    logger.info("Weatherbot begin")
    main_nws()
    main_nhc()
    logger.info("Weatherbot complete")


   
if __name__ == "__main__":
    main()
