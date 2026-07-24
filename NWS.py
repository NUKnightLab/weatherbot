import json
import logging
import re

import requests

from util import (
    Translator,
    convert_time,
    headline_to_gmt_minus_4,
    load_parsed_data,
    render_template,
    save_parsed_data,
)

logger = logging.getLogger('NWS')


def fetch_nws_data():
    logger.debug("fetching NWS data")
    # TODO consolidate all NWS specific behavior in one place, probably NWS.py
    ###NWS PRODUCTS     
    apiurl = "https://api.weather.gov/alerts/active/area/PR"
    headers = {"accept": "application/geo+json" , 
           "User-Agent": "El Vocero / AP / Knight Lab Weatherbot" 
           }

  
    response = requests.get(apiurl, headers=headers)
    #add url for product nhc

    if response.ok:
        return response.json()
    else:
        logger.warning(f"NWS API request NOT OK: {response.status_code}")
        return None


def get_weather_bulletin(bulletin, test_mode) -> list:
    PARSED_ID_FILE = 'NWSdata.json'
    translate = Translator()

    data = []

    relevant_stories= { # if there's an image that should be posted for a given story type, include the code here.
        'flash flood warning': 'aviso_de_inundaciones',
        'flood warning': None,
        'flash flood watch': 'vigilancia_de_inundaciones', 
        'flood advisory': None, 
        'special weather statement': 'reporte_especial',
        'hurricane local statement': 'reporte_especial_de_huracan', 
        'heat advisory': 'calor_extremo', 
        'heat warning': 'calor_extremo', 
        'rip current statement': None
    }

    #pub date , end time , event , areas affected, headline , what , where , impacts 
   
    parsed_ids=load_parsed_data(PARSED_ID_FILE) 

    with open(bulletin) as f :
        bulletin = json.load(f)

        if bulletin['features'] == []:
            logger.debug("No weather alerts")
            return []

        for feature in bulletin['features']:
            event = feature['properties']['event'].casefold()
            
            eventid=feature["id"]
 
            if eventid in parsed_ids and not test_mode:
                logger.debug(f"Skipping '{event}' -- already processed. [id: {eventid}]")
                continue

            if not event in relevant_stories :
                logger.debug(f"Skipping '{event}' -- not relevant")
                continue

            parsed_ids[eventid]=True
            
            eventdict = {}
            eventdict['event'] = translate(event)
            eventdict['image_code'] = relevant_stories[event]
            eventdict['@id'] = eventid
            refs= []
            for ref in feature['properties']['references']:
                refs.append({'@id': ref['@id'], 'sent': ref['sent']})
            eventdict['references'] = refs

            #print(refs)
            
            areas = feature['properties']['areaDesc'].split(";")
            areas = [translate(area.split(",")[0].strip()) for area in areas]

            eventdict['areas_affected'] = format_list_strings(areas)
            if len(areas) == 1:
                eventdict['onearea'] = True
            #print('areas affected', eventdict['areas_affected'])
            #print('Areas affected:', eventdict['areas_affected'])
            eventdict['sent'] =convert_time(feature['properties']['sent'] , format="NWS")
            eventdict['effective'] = convert_time(feature['properties']['effective'] , format="NWS")
            eventdict['expires'] = convert_time(feature['properties']['expires'] , format="NWS")
            headline =headline_to_gmt_minus_4(feature['properties']['headline'], eventdict['effective'], eventdict['expires'])
            eventdict['headline'] = translate(headline)
            description = feature['properties']['description']
            #print('Headline:', headline)
            eventdict['description'] = translate(description)

            description_dict = process_description(description, translate)

            if len(description_dict) > 0:
                eventdict.update(description_dict)
            else:
                logger.warning(f"process_description() came up empty for {eventid}")
                eventdict['use_description'] = True
                    

            data.append(eventdict)
            logger.info(f"Added [{event}] [{eventid}] to data")

        if type(parsed_ids) == dict and not test_mode:
            save_parsed_data(parsed_ids, PARSED_ID_FILE)
        else:
            logger.warning(f"save_parsed_data got non-dict (or test mode), so not saving {parsed_ids}")

    return data

DESCRIPTION_EXTRACTORS = [
        (re.compile(r"^\* WHAT"), 'what', lambda line: line.split("...")[1]),
        (re.compile(r"^\* WHERE"), 'where', lambda line: line.split("...")[1]),
        (re.compile(r"^\* WHEN"), 'when', lambda line: line.split("...")[1]),
        (re.compile(r"^\* IMPACTS"), 'impacts', lambda line: line.split("...")[1]),
        (re.compile(r"^\* RAIN"), 'rain', lambda line: line.split("...")[1]),
        (re.compile(r"^\* WIND"), 'wind', lambda line: line.split("...")[1]),
        (re.compile(r"^\* STORM SURGE"), 'storm_surge', lambda line: line.split("...")[1]),
]
def process_description(description: str, translate: callable) -> dict:
    d = {}
    lines = description.split("\n\n")
    for line in lines:
        for pat, key, func in DESCRIPTION_EXTRACTORS:
            if pat.match(line):
                d[key] = translate(func(line))
    return d

def format_list_strings(strings):
    if len(strings) == 0:
        return ""
    elif len(strings) == 1:
        return strings[0]
    else:
        last_string = strings[-1]
        other_strings = ", ".join(strings[:-1])
        return f"{other_strings}, y {last_string}"



# Given a bulletin from the NWS, see if stories should be written
# for each event that needs a story, generate the content 
# return a list of story content for dispatch elsewhere
def generate_nws_stories(bulletin, test_mode=False) :
    data = get_weather_bulletin(bulletin, test_mode)

    generated_stories=[]

    for event in data:
        new_story = render_template('story_templates/NWS.html', data=event)
        generated_stories.append({
            "content" : new_story, 
            "headline": event["headline"],
            'image_code': event.get('image_code'),
            'event_id': event.get('@id', 'event ID missing')
            })

    return generated_stories
