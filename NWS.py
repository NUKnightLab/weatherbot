import json 
from util import load_parsed_data, render_template, save_parsed_data, contains_area, Translator,convert_time, headline_to_gmt_minus_4
from jinja2 import Template, Environment, FileSystemLoader
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import re

import logging
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
    areas = ["puerto rico", "vieques","culebra" , "pr"]

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
            
            for i in range(len(areas)):
                if contains_area(areas[i], areas):
                    areas[i]=translate(areas[i].split(",")[0].strip())
                else :
                    areas.pop(i)
                 
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
            eventdict.update(description_dict)

            data.append(eventdict)

        if type(parsed_ids) == dict and not test_mode:
            save_parsed_data(parsed_ids, PARSED_ID_FILE)
        else:
            logger.warning(f"save_parsed_ids got non-dict, so not saving {parsed_ids}")

    return data

DESCRIPTION_EXTRACTORS = [
        (re.compile("^\* WHAT"), 'what', lambda line: line.split("...")[1]),
        (re.compile("^\* WHERE"), 'where', lambda line: line.split("...")[1]),
        (re.compile("^\* WHEN"), 'when', lambda line: line.split("...")[1]),
        (re.compile("^\* IMPACTS"), 'impacts', lambda line: line.split("...")[1]),
        (re.compile("^\* RAIN"), 'rain', lambda line: line.split("...")[1]),
        (re.compile("^\* WIND"), 'wind', lambda line: line.split("...")[1]),
        (re.compile("^\* STORM SURGE"), 'storm_surge', lambda line: line.split("...")[1]),
]
def process_description(description: str, translate: callable) -> dict:
    d = dict()
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
            'image_code': event.get('image_code')
            })

    return generated_stories

# TODO consider a dict of linestart pattern keys/eventdict key values instead of long if/else
def test0 ():
    desc="The National Weather Service in Las Vegas has extended the\n\n* Flash Flood Warning for...\nNorthwestern Clark County in southern Nevada...\n\n* Until 1230 PM PDT.\n\n* At 923 AM PDT, Excessive runoff in creeks and washes from the\nearlier heavy rain fall continues around Mount Charleston. Flash\nflooding is ongoing.\n\nHAZARD...Life-threatening flash flooding. Heavy rain producing\nflash flooding.\n\nSOURCE...Video and gauges reports.\n\nIMPACT...Life-threatening flash flooding of low-water\ncrossings, creeks, normally dry washes and roads.\n\n* Some locations that will experience flash flooding include...\nRainbow Canyon, Mt. Charleston, Spring Mountains, Hilltop\nCampground, Mahogany Grove Campground, Kyle Canyon Campground,\nFletcher View Campground, Mary Jane Falls Campground, Dolomite\nCampground and Mcwilliams Campground.\n\nPlease stay away from Mount Charleston as signficant flooding and\nflood damage has occurred."
    description= "RRA\n\n* WHAT...Small stream flooding caused by excessive runoff.\n\n* WHERE...Patillas.\n\n* WHEN...Until 315 PM AST.\n\n* IMPACTS...Rises in small streams and rivers, particularly Rio\nPatillas and its tributaries.\n\n* ADDITIONAL DETAILS...\n- At 129 PM AST, Excessive runoff will continue to cause small\nstream flooding and sharp rises along rivers.\n- http://www.weather.gov/safety/flood"
    eventdict = {}
    lines = desc.split("\n\n")
    eventdict["event"]="ffw"
            #line starting with * WHAT
    for line in lines:
        if line.startswith("* WHAT"):
            
            eventdict['what'] = translate(line.split("...")[1])
            

            # print("what", eventdict['what'])
        elif line.startswith("* WHERE"):
            eventdict['where'] = translate(line.split("...")[1])
            # print("where", eventdict['where'])
        elif line.startswith("* WHEN"):
            eventdict['when'] = translate(line.split("...")[1])
            # print("when", eventdict['when'])
        elif line.startswith("HAZARD"):
            eventdict['hazard'] = translate(line.split("...")[1])
            # print("when", eventdict['when'])
        elif line.startswith("* IMPACTS") or line.startswith("IMPACT") :
            eventdict['impacts'] = translate(line.split("...")[1])
            # print("impacts", eventdict['impacts'])
        elif line.startswith("* RAIN") :
            eventdict['rain'] = translate(line.split("...")[1])
            # print("rain", eventdict['rain'])
        elif line.startswith("* WIND") :
            eventdict['wind'] = translate(line.split("...")[1])
            # print("wind", eventdict['wind'])
        elif line.startswith("* STORM SURGE") :
            eventdict['storm_surge'] = translate(line.split("...")[1])
            # print("storm_surge", eventdict['storm_surge'])

    print( "what" not in eventdict.keys() and "hazard" in eventdict.keys() and "impacts" in eventdict.keys())
    template=" <p> {{data.what}} </p> <p> {{data.hazard}} </p> <p> {{data.impacts}} </p> "
    template = Template(template)
    rendered = template.render(data=eventdict)
    soup = BeautifulSoup(rendered, 'html.parser')
    p_tags= soup.find_all('p')
    text='\n'.join([ elem.get_text() for elem in p_tags])
    print(text)

    


if __name__ == '__main__':
    
    test0()
