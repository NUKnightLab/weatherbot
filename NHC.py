import re
from bs4 import BeautifulSoup

from util import get_translator_func,load_parsed_data , save_parsed_data,contains_area
from jinja2 import Template

import logging
logger = logging.getLogger('NHC')

def clean_str(str):
    str= re.sub(r'[^\w]', '', str).strip()
    return str

def get_tropical_bulletin(bulletin):
    PARSED_ID_FILE = 'NHCdata.json'

    translate = get_translator_func()

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
    if stormname in parsed_ids:
        logger.debug(f"ID '{stormname}' has already been processed. Skipping...")
        signals["skip"] = True
        return results
    else:
        logger.debug(f"Processing ID '{stormname}'...")
        parsed_ids[stormname] = True
    name_pattern= r'\b([A-Za-z]+) (?:Intermediate|Advisory)'
    name_match = re.search(name_pattern, stormname)
    data["stormname"] = name_match.group(1)

    
    data["event"] = stormname
    

    
    for item in items :
        
        desc = item.find('description')
        desc = desc.text
        headers = desc.split("BULLETIN")[1].split("SUMMARY OF")[0]
        headers = headers.strip().split("\n")
        headers = [line for line in headers if line != '']
        #TIME OF BULLETIN   
        data["published"]= " ".join(headers[2].split(" ")[0:4]).strip()
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
        if warnings.__contains__("There are no coastal watches or warnings in effect.") or len(matches) == 0:
            signals["nowarning"] = True
            
            
        if warnings.__contains__("CHANGES WITH THIS ADVISORY:"):
            changes = desc.split("CHANGES WITH THIS ADVISORY:", 1)[1].split("SUMMARY OF WATCHES AND WARNINGS IN EFFECT:",1)[0]
            
            if changes.__contains__("None") or not contains_area(changes, area):
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
                event = {}
                event["type"] = match
                event["places"] = []  
                event["relevant"] = False
                index = warnings.index("A " +match+ " is in effect for...") +1
                #find all events and for each event places 
                while index < len(warnings) and warnings[index] != '$':
                    place = warnings[index].replace("* ", "").strip()
                    event["places"].append(translate(place))
                    if place.casefold().__contains__("puerto rico"):
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
    
                if sentence.__contains__("...") :
                
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
                elif sentence.__contains__(":"):
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
            if count == 0:
                if contains_area(sentences[0], area):
                    hazardflags["rain"] = True
                    hazardflags["rainfacts"] = True
                    rainlist= translate(sentences[0].replace("\n", "").strip())
            data["rain"] = rainlist
                    
            
        surgepattern = r"\b(?:SURGE|STORM SURGE):(.+?)\.\s*(?:RAINFALL:|WIND:|TORNADOES:|NEXT ADVISORY)"
        
        
        surgedata = re.search(surgepattern, hazards, re.DOTALL)
        
        if surgedata:
            if surgedata.group(1).__contains__("..."):

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
            

    
    save_parsed_data(parsed_ids, PARSED_ID_FILE)

    return results

# not sure how to mark type for bulletin which is a FLO (either StringIO or file opened by argparse)
def writeNHC(bulletin) -> dict: 
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

    results = get_tropical_bulletin(bulletin)
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
                with open("templates/story_templates/" + eventtype + ".html") as f:
                    template = Template(f.read())
                    new_story = template.render(data=results['data'], event=event, flags=results['flags'], signals=results['signals'])
                    soup = BeautifulSoup(new_story, 'html.parser')
                    p_tags= soup.find_all('p')
                    
                    new_story= [re.sub(r'\s+', ' ', p.get_text(strip=True)) for p in p_tags if p.get_text(strip=True)]
                    with open("templates/email_templates/storypublished.html") as f:
                        emailtemplate = Template(f.read())
                        emailcontent = emailtemplate.render(data=results['data'], event=event, flags=results['flags'], signals=results['signals'])
                        emailcontent= BeautifulSoup(emailcontent, 'html.parser').find_all('p')
                        emailcontent= [re.sub(r'\s+', ' ', p.get_text(strip=True)) for p in emailcontent if p.get_text(strip=True)]
                    new_story={
                        "body": '\n'.join(new_story), 
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

                    
    logger.warning(f"writeNHC finished with no clear return value")
    return {}
                        

    

    
    
   
   

                    
            





             
             
             

             
            
             
             
         
      

    
if __name__ == '__main__':
    #description = "<![CDATA[ <pre> 000 WTPZ31 KNHC 290231 TCPEP1 BULLETIN Hurricane Adrian Advisory Number 6 NWS National Hurricane Center Miami FL EP012023 900 PM MDT Wed Jun 28 2023 ...ADRIAN CONTINUES MOVING SLOWLY WESTWARD... SUMMARY OF 900 PM MDT...0300 UTC...INFORMATION ---------------------------------------------- LOCATION...15.4N 109.0W ABOUT 395 MI...640 KM SW OF MANZANILLO MEXICO MAXIMUM SUSTAINED WINDS...80 MPH...130 KM/H PRESENT MOVEMENT...W OR 280 DEGREES AT 6 MPH...9 KM/H MINIMUM CENTRAL PRESSURE...986 MB...29.12 INCHES WATCHES AND WARNINGS -------------------- CHANGES WITH THIS ADVISORY: None. There are no coastal watches or warnings in effect. DISCUSSION AND OUTLOOK ---------------------- At 900 PM MDT (0300 UTC), the center of Hurricane Adrian was located near latitude 15.4 North, longitude 109.0 West. Adrian is moving toward the west near 6 mph (9 km/h). A slow motion toward the west or west-northwest is expected during the next few days. Maximum sustained winds are near 80 mph (130 km/h) with higher gusts. Some additional strengthening is forecast into Thursday. Weakening is likely to begin Thursday night or Friday. Hurricane-force winds extend outward up to 15 miles (30 km) from the center and tropical-storm-force winds extend outward up to 80 miles (130 km). The estimated minimum central pressure is 986 mb (29.12 inches). HAZARDS AFFECTING LAND ---------------------- None NEXT ADVISORY ------------- Next complete advisory at 300 AM MDT. $$ Forecaster Pasch </pre> ]]>"
    #get from dir the latest xml filclee
   
        # print(bulletin)
        #[no_warning , no_update , practive , raintranslate ,surgetranslate , interest]
        

        # print(data)

    #print(data['location'])
    print("test")

    testdata= writeNHC("test.xml")

    print(testdata)
       


    

 
  
    
    
   
    
