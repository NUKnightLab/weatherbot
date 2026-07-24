import logging
import re

from bs4 import BeautifulSoup
from jinja2 import Template

from util import (
    Translator,
    contains_area,
    convert_time,
    load_parsed_data,
    render_template,
    save_parsed_data,
)

logger = logging.getLogger('NHC')

def clean_str(str):
    str= re.sub(r'[^\w]', '', str).strip()
    return str

def get_tropical_bulletin(bulletin, test_mode):
    PARSED_ID_FILE = 'NHCdata.json'

    translate = Translator()

    parsed_ids = load_parsed_data(PARSED_ID_FILE)
    separatorpattern = r"\.\s+"
    area = ["puerto rico", "vieques","culebra"]  

    data = {}
    signals= {"nowarning": False, "noupdate": False, "practive": False, "interest": False , "skip": False}
    hazardflags= {"rain": False, "surge": False, "tornadoes": False, "surf": False, "rainfacts": False, "surgefacts": False}
    results = {
        'data': data,
        'flags': hazardflags,
        'signals': signals        
    }

    soup = BeautifulSoup(bulletin , features="xml")

    items = soup.find_all('item')
    stormname = soup.find('title').text.strip()
    if stormname in parsed_ids and not test_mode:
        logger.debug(f"ID '{stormname}' has already been processed. Skipping...")
        signals["skip"] = True
        return results
    else:
        logger.debug(f"Processing ID '{stormname}'...")
        parsed_ids[stormname] = True

    time_published = soup.find('pubDate').text.strip()
    data["published"] = convert_time(time_published , format = "NHC")
    name_pattern= r'\b([A-Za-z]+) (?:Intermediate|Advisory)'
    name_match = re.search(name_pattern, stormname)
    data["stormname"] = name_match.group(1)
    data["event"] = stormname

    

    
    for item in items :
        
        desc = item.find('description')
        desc = desc.text.replace('<br />','')
        headers = desc.split("BULLETIN")[1].split("SUMMARY OF")[0]
        headers = headers.strip().split("\n")
        headers = [line for line in headers if line != '']
        #TIME OF BULLETIN   
        headline = "/e".join(headers[3:])
        headline= headline.replace("...","").strip()
        headline= headline.replace("/e"," ")
        data["headline"] = translate(headline.lower().capitalize())
        
        summary = desc.split("INFORMATION")[1].split("WATCHES")[0]
        #Storm Center Location
        location_pattern = r"LOCATION\.\.\.(.*)"
        location_match = re.search(location_pattern, summary)
        assert len(location_match.groups()) == 1
        data["location"] = location_match.group(1)
        #Reference to the nearest known land location
        nearest_pattern = r"ABOUT\s+(\d+)\s+(MI|KM)\.{3}(\d+)\s+(MI|KM)(?:\s+(\w)\s*)?[\s\S]*?OF\s+(\w.*)"
        matches = re.findall(nearest_pattern,summary, re.IGNORECASE)
        distances = []
        
        for match in matches:
            
            distance = f"{match[0]} {match[1]} {match[4]} de {match[5].title()}"
            
            distances.append(distance.strip())
        
        data["distances"] = distances
        #movement and direction speed of the storm
        movement_pattern = r"PRESENT MOVEMENT\.\.\.(.*)"
        movement_match = re.findall(movement_pattern, summary)
        assert len(movement_match) == 1
        movement = movement_match[0].split("...")[0]
        movement = movement.split(" ") 
        data["movement"] = movement[0] + " a " + " ".join(movement[5:])
    
        #maximun sustained winds
        winds_pattern = r"MAXIMUM SUSTAINED WINDS\.\.\.(.*)"
        winds_match = re.findall(winds_pattern, summary)
        assert len(winds_match) == 1
        data["winds"] = winds_match[0].split("...")[0]

        #central pressure
        pressure_pattern = r"MINIMUM CENTRAL PRESSURE\.\.\.(.*)"
        pressure_match = re.findall(pressure_pattern, summary)
        assert len(pressure_match) == 1
        data["pressure"] = pressure_match[0].split("...")[0]
    
    # alerts and warnings
        
        warnings = desc.split("WATCHES AND WARNINGS", 1)[1].split("DISCUSSION AND OUTLOOK",1)[0]
        matches = re.findall(r'A ([\w\s]+) is in effect for\.\.\.', warnings)
        if "There are no coastal watches or warnings in effect." in warnings or len(matches) == 0:
            signals["nowarning"] = True
            
            
        if "CHANGES WITH THIS ADVISORY:" in warnings:
            changes = desc.split("CHANGES WITH THIS ADVISORY:", 1)[1].split("SUMMARY OF WATCHES AND WARNINGS IN EFFECT:",1)[0]
            
            if "None" in changes or not contains_area(changes, area):
                signals["noupdate"] = True
                
        
        
        interests= re.search(r'\bInterests elsewhere\b[^.]*\.', warnings, re.IGNORECASE)
        
        if interests and contains_area(interests.group(0), area):
            data["interests"] = translate(interests.group(0)).lower()
            signals["interest"] = True
        warnings = warnings.split("\n")
        for i in range(len(warnings)) :
            warnings[i] = warnings[i].strip()
            
            if warnings[i]=="" or warnings[i]==" ":
                warnings[i] = "$"
        

        #find warnings and watches in effect
        
        data["events"] = []
        for match in matches: 
            try:
                event = {
                    'type': match,
                    'places': [],
                    'relevant': False
                }
                index = warnings.index("A " +match+ " is in effect for...") +1
                #find all events and for each event places 
                while index < len(warnings) and warnings[index] != '$':
                    place = warnings[index].replace("* ", "").strip()
                    if "puerto rico" in place.casefold():
                        event["places"].append(translate(place))
                        event["relevant"] = True

                        
                    index += 1
                data["events"].append(event)
            except ValueError as e:
                logger.warning(f"Error making event for match [{match}] {e}")

        data["practive"] = []

        for event in data["events"]:
            if event["relevant"] == True :
                data["practive"].append(event)
                signals["practive"] = True
            else:
                logger.debug(f"event {event['type']} not deemed relevant")

        #hazards affecting land
        hazards = desc.split("HAZARDS AFFECTING LAND",1)[1].split("FORECASTER",1)[0]
        #rainfall
        rainpattern = r"RAINFALL:(.*?)\.\s*(?:WIND:|TORNADOES:|SURF:|NEXT ADVISORY|STORM SURGE:|$$)"
        raindata = re.search(rainpattern, hazards, re.DOTALL)
        
        if raindata:
            rain = raindata.group(1)
            sentences = re.split(separatorpattern, rain)
            rainlist = []
            count = 0
            
            
            for sentence in sentences:
                sentence = sentence.strip().replace("\n", "")
                location_amount = {}
    
                if "..." in sentence:
                
                        location = sentence.split("...")[0]
                        height = sentence.split("...")[1]
                        if contains_area(location, area):
                            hazardflags["rain"] = True
                            if contains_area(height, area):
                            
                                location_amount["location"] = None
                                location_amount["height"] = translate(height)
                            else :
                                location_amount["location"] = translate(location)
                                location_amount["height"] = translate(height)
                            count += 1
                            rainlist.append(location_amount)
                elif ":" in sentence:
                    location = sentence.split(":")[0]
                    height = sentence.split(":")[1]
                    if contains_area(location, area):
                        hazardflags["rain"] = True
                        if contains_area(height, area):
                            location_amount["location"] = None
                            location_amount["height"] = translate(height)
                        else :
                            location_amount["location"] = translate(location)
                            location_amount["height"] = translate(height)
                        count += 1
                        rainlist.append(location_amount)
            if count == 0 and contains_area(sentences[0], area):
                hazardflags["rain"] = True
                hazardflags["rainfacts"] = True
                rainlist= translate(sentences[0].replace("\n", "").strip())
            data["rain"] = rainlist
                    
            
        surgepattern = r"\b(?:SURGE|STORM SURGE):(.+?)\.\s*(?:RAINFALL:|WIND:|TORNADOES:|NEXT ADVISORY)"
        
        
        surgedata = re.search(surgepattern, hazards, re.DOTALL)
        
        if surgedata:
            if "..." in surgedata.group(1):

                surgedata= surgedata.group(1).split("...", 1) [1]
                patt= r'([A-Za-z\s.-]+)\.\.\.(\d+\s+to\s+\d+)\s+ft'
                surgesentences = re.findall(patt, surgedata, re.DOTALL)
                surgelist = []
                for surge in surgesentences:
                
                    location= surge[0].strip()
                    height = surge[1].strip()+' ft'
                    if contains_area   (location, area):
                        hazardflags["surge"] = True
                        surgelist.append({"location": translate(location), "height": translate(height)})
                data["surge"] = surgelist
            else:
                surgesentences = surgedata.group(1).split(".")[0]
                if contains_area(surgesentences, area):
                    hazardflags["surge"] = True
                    hazardflags["surgefacts"] = True
                    data["surge"] = translate(surgesentences[0])
            #surf
            
        surfpattern = r"\b(?:SURF|SWELLS):(.+?)\.\s*(?:RAINFALL:|WIND:|TORNADOES:|NEXT ADVISORY)"

        surfdata = re.search(surfpattern, hazards, re.DOTALL)
        
        if surfdata:   
            
            surfdata = re.split(separatorpattern, surfdata.group(1))[0]
            if contains_area(surfdata, area):
                surfdata = translate(surfdata).strip().casefold()
                hazardflags["surf"] = True
                
                data["surf"] = surfdata
            


        #tornadoes
        tornadopattern = r"\b(?:TORNADOES):(.+?)\.\s*(?:RAINFALL:|WIND:|SURF:|NEXT ADVISORY)"
        tornadodata = re.search(tornadopattern, hazards, re.DOTALL)
        if tornadodata:
            tornadodata = re.split(separatorpattern, tornadodata.group(1))[0]
            if contains_area(tornadodata, area):
                tornadodata = translate(tornadodata).strip()
                hazardflags["tornadoes"] = True
                data["tornadoes"] = tornadodata
            

    if not test_mode:
        save_parsed_data(parsed_ids, PARSED_ID_FILE)

    return results

# not sure how to mark type for bulletin which is a FLO (either StringIO or file opened by argparse)
def writeNHC(bulletin, test_mode=False) -> dict: 
    """Given a file-like object representing an NHC XML file, parse it, analyze it,
    and return a dictionary. This dictionary may be empty, or it may have various keys
    which govern what should be done based on the bulletin's contents, including posting 
    to the El Vocero CMS and/or sending email notifications. The actual posting and sending
    happen outside of this function. 
    """
    IMAGE_CODES = {
        'hurricanewarning': 'aviso_de_huracan',
        'hurricanewatch': 'vigilancia_de_huracan',
        'stormsurgewatch': 'vigilancia_de_inundaciones',
        'tropicalstormwarning': 'aviso_de_tormenta_tropical',
        'tropicalstormwatch': 'vigilancia_de_tormenta_tropical',
    }

    results = get_tropical_bulletin(bulletin, test_mode)
    if results['signals']['skip']:
        return {}

    generated_stories = []
    if results['signals']["practive"]:
        logger.debug("writeNHC: practive")
        if results['signals']["noupdate"]:
            logger.debug("no update for active warning")
            event = results['data']['practive'][0]
            with open("templates/email_templates/no_update.html") as f:
                template= Template(f.read())
                new_story = template.render(data=results['data'], flags=results['flags'] , signals=results['signals'])
                return {
                    "content": {
                        "body": new_story, 
                        "headline": results['data']["headline"], 
                        "event": event["type"]
                    },
                    "action":"email"
                }
        else:
            for event in results['data']["practive"]: 
                eventtype= event["type"].replace(" ", "").lower()
                rendered = render_template(f"story_templates/{eventtype}.html", 
                                            data=results['data'], 
                                            event=event, 
                                            flags=results['flags'], 
                                            signals=results['signals'])
                with open("templates/email_templates/storypublished.html") as f:
                    emailtemplate = Template(f.read())
                emailcontent = emailtemplate.render(data=results['data'], event=event, flags=results['flags'], signals=results['signals'])
                emailcontent= BeautifulSoup(emailcontent, 'html.parser').find_all('p')
                emailcontent= [re.sub(r'\s+', ' ', p.get_text(strip=True)) for p in emailcontent if p.get_text(strip=True)]
                new_story={
                    "body": rendered, 
                    "headline": results['data']["headline"] , 
                    "event": event["type"], 
                    "email": '\n'.join(emailcontent),
                    'image_code': IMAGE_CODES.get(eventtype)
                }
                generated_stories.append(new_story)
            return {
                "content": generated_stories, 
                "action":"post" 
            }
    elif results['signals']["nowarning"]:
        logger.debug('not relevant')
        eventtype= "no_warning"
        with open("templates/email_templates/informational.html") as f:
            template= Template(f.read())
            new_story = template.render(data=results['data'] , flags=results['flags'] , signals = results['signals'])
            soup = BeautifulSoup(new_story, 'html.parser')
            p_tags= soup.find_all('p')
            new_story='\n'.join([ elem.get_text() for elem in p_tags])
            new_story={"body": new_story , "headline": results['data']["headline"] }
        return {
            "content": new_story, 
            "action":"email"
        }

    logger.warning("writeNHC finished with no clear return value")
    return {}
