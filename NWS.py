import json 
from util import load_parsed_data, save_parsed_data, contains_area, Translator
from jinja2 import Template
from datetime import datetime
import requests
from bs4 import BeautifulSoup

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


def get_weather_bulletin(bulletin):
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
            return {"data":None , "action":"pass"}

        for feature in bulletin['features']:
            event = feature['properties']['event'].casefold()
            
            eventid=feature["id"]
 
            if eventid in parsed_ids:
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
            eventdict['headline'] = translate(feature['properties']['headline'])
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
            eventdict['sent'] = feature['properties']['sent']
            time_format = '%Y-%m-%dT%H:%M:%S%z'

            effective = feature['properties']['effective']
            time_obj = datetime.strptime(effective, time_format)
            eventdict['effective'] = time_obj.strftime(('%I:%M %p')) + " AST" 
            expire = feature['properties']['expires']
            time_obj = datetime.strptime(expire, time_format)
            eventdict['expires'] = time_obj.strftime(('%I:%M %p')) + " AST" 
            
            description = feature['properties']['description']
            #print('Headline:', headline)
            eventdict['description'] = translate(description)
            #print(description)
            lines = description.split("\n\n")
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
                elif line.startswith("* IMPACTS"):
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
          
            data.append(eventdict)

        if type(parsed_ids) == dict:
            save_parsed_data(parsed_ids, PARSED_ID_FILE)
        else:
            logger.warning(f"save_parsed_ids got non-dict, so not saving {parsed_ids}")

    return data


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
def generate_nws_stories(bulletin) :
    data = get_weather_bulletin(bulletin)

    generated_stories=[]

    for event in data:

        with open("templates/story_templates/NWS.html") as f :
            template = Template(f.read())
            new_story = template.render(data=event)
            soup = BeautifulSoup(new_story, 'html.parser')
            p_tags= soup.find_all('p') # TODO this seems uncomfortably confident that no one will ever change the templates to use other than p tags. isn't there another way to get content out of a soup?

            new_story='\n'.join([ elem.get_text() for elem in p_tags])
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
