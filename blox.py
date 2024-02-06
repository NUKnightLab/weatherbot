import json
import os
import requests
from datetime import datetime, timedelta
from pathlib import Path

import logging
logger = logging.getLogger('blox')

AUTH_OK = False
try:
    AUTH_USER = os.environ['AUTH_USER']
    AUTH_SECRET = os.environ['AUTH_SECRET']
    AUTH_OK = True
except KeyError:
    logger.warn("CMS API configuration error. AUTH_USER and AUTH_SECRET must be set as environment variables. Articles will not be posted.")

WS_ROOT = 'https://www.elvocero.com/tncms/webservice/v1/'



def make_cms_link(internal_id):
    return f"https://admin-newyork1.bloxcms.com/elvocero.com/editorial/article/{internal_id}"

def post_story(headline, content, image_code=None, actually_post_articles=False):
    """Given materials relevant to a new article to be created in the CMS,
        execute the HTTP POST to create it.

        Images get uploaded every time. We were advised by Blox that there can be problems if there are too many
        relationships to the same image asset ID.

        Parameters:
            headline: a string
            content: a string
            image_code (optional): a code for one of the valid images we use. If provided, it will be uploaded, and also used as the preview.
      """

    # https://www.elvocero.com/tncms/webservice/#operation/editorial_create_asset_with_files
    url = f"{WS_ROOT}editorial/create_asset"

    if not actually_post_articles:
        logger.info("Post article flag not set. Details at debug level.")
    elif not AUTH_OK:
        logger.info("CMS authorization improperly configured. Articles will not be posted. Article details logged at debug level")
        actually_post_articles = False

        

    now = datetime.now()
    start_time = now + timedelta(days=365*100) # during testing, use a date far in the future because stories go live when this date is now or past

    data = {
        'id': f'knightlab-bot-{now.isoformat()}',
        'type': 'article',
        'title': headline,
        'byline': 'Redaccion El Vocero',
        'content': content,
        'start_time': start_time.isoformat(), 
        'keywords': ['weatheralert'], # do they want anything here?
        'sections': ['alertasdeltiempo '], # ['weather'],
        'flags': ["weather_alert"],
        'source_app': 'editorial'
    }

    if image_code:
        if actually_post_articles:
            image_id = post_image(image_code)
            data['relationships'] = [{
                'id': image_id,
                'is_internal': True,
                'type': 'child',
                'app': 'editorial'
            }]
        else:
            preview_image_path = get_image(image_code)
            logger.debug(f"would have posted image code: {image_code} {preview_image_path}")

    files = {
        'metadata': ('story.json', json.dumps(data), 'application/json')
    }

    if actually_post_articles:
        if image_code: # need to test this twice because of the different places the images go
            preview_image_path = get_image(image_code)
            files['preview'] = preview_image_path.open('rb')

        resp = requests.post(url, auth=(AUTH_USER,AUTH_SECRET), files=files)

        if resp.ok:
            resp_json = resp.json()
            internal_id = resp_json['internalid']
            logger.info(f"posted story {internal_id}")
            return internal_id
        else:
            logger.warning(f"Failed to post [{headline}] response code [{resp.status_code}]")
            logger.warning(resp.text)
            return None
    else:
        logger.debug("article content:")
        logger.debug(json.dumps(data, indent=2))
        logger.debug('-------')
        return 'fake-internal-article-id'

def get_image(image_code):
    img_path = Path(f"images/{image_code}.jpg")
    if not (img_path.exists and img_path.is_file()):
        raise ValueError(f"{image_code} is not a valid file")
    return img_path

def post_image(image_code):
    """Given a coded image identifier, post that image to the CMS and return its internal ID
    For now, image codes are just the filename part of images in the `images` directory, 
    assumed to be JPG.
    """

    img_path = get_image(image_code)

    url = f"{WS_ROOT}editorial/create_asset"
    now = datetime.now()
    data = {
        'id': f'knightlab-bot-image-{image_code}-{now.isoformat()}',
        'type': 'image',
        'title': f'Weatherbot Image {image_code} posted at {now.strftime("%Y-%m-%d %H:%M:%S")} by Knight Lab Code',
        'byline': 'Redaccion El Vocero',
        'source_app': 'editorial'
    }
    resp = requests.post(url, auth=(AUTH_USER,AUTH_SECRET), 
                        files={
                            'metadata': ('story.json', json.dumps(data), 'application/json'),
                            'image': img_path.open('rb')
                        }
    )
    logger.debug(f"Posted image {image_code} got {resp.status_code}")
    if resp.ok:
        resp_json = resp.json()
        return resp_json['internalid']
    else:
        logger.warning(f"Failed to post image [{image_code}] response code [{resp.status_code}]")
        return None


def post_test_story():
    content = """
<p>Qui laborum minim nisi aliquip dolore dolore cillum dolore. Quis do consequat cillum ea dolore sint. Labore officia magna voluptate minim velit id cupidatat in minim dolore irure. Aliquip dolore excepteur culpa anim sunt nostrud commodo commodo consequat nisi incididunt nostrud tempor.</p>
<p>Exercitation elit cupidatat ea nostrud non dolore amet ex enim id. Non duis ullamco deserunt officia aliquip enim non cupidatat qui. Duis ad commodo non magna enim laborum ad sunt mollit. Excepteur sunt laboris et minim voluptate aliquip irure eiusmod non ipsum nulla. Voluptate excepteur incididunt eu fugiat est dolore laborum. Ea irure laboris cillum reprehenderit labore ad nulla irure velit ipsum deserunt esse dolor Lorem. Aliquip aliqua ut esse deserunt adipisicing cupidatat ut tempor ex dolore.</p>
<p>Laboris nulla nisi ut adipisicing aliqua Lorem ea ea quis pariatur sint. Mollit sit nulla nisi amet aliquip voluptate. Magna qui minim Lorem enim eu commodo consectetur fugiat id. Quis do duis officia commodo do ullamco exercitation excepteur consequat do nisi.</p>
<p>Laborum ea laborum esse excepteur labore aliquip deserunt nostrud sunt eu. Incididunt enim in id culpa voluptate dolore fugiat laborum. Elit tempor qui velit aute. Laborum aute est anim nisi id pariatur aliquip officia id enim est.</p>
"""
    now = datetime.now()
    response = post_story(f"{now.isoformat()} Test story", content, 'aviso_de_huracan')
    return response 

# https://www.elvocero.com/tncms/webservice/#operation/editorial_search
def search(q='Knight Lab'): 
    """Was maybe going to be a generalized search, but we don't need that so i tuned it to what i needed"""
    url = f"{WS_ROOT}editorial/search"
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    query = {
        'q': q,
        'admin': True,
        'l': 100,
        'o': 0
    }
    items = []
    keep_going = True
    try:
        while(keep_going):
            resp = requests.post(url, auth=(AUTH_USER,AUTH_SECRET), headers=headers, data=query)
            if not resp.ok:
                break
            data = resp.json()
            data['limit'] = int(data['limit'])
            data['offset'] = int(data['offset'])
            for item in data['items']:
                if item['type'] == 'image':
                    if "Weatherbot" in item['title']:
                        items.append(item)
                    else:
                        print(f"Skipping likely foreign image f{item['title']} [{item['id']}]")
                elif item['type'] == 'article':
                    if item['start_time'].startswith('2123'):
                        items.append(item)
                    else:
                        print(f"Skipping live article {item['title']} [{item['id']}]")
                else:
                    print(f"Skipping other type {item['type']} {item['title']} [{item['id']}]")
            if data['offset'] + data['limit'] > data['total']: break
            query['o'] = query['o'] + data['limit']
    except Exception as e:
        import pdb; pdb.set_trace()
    return items        

def get(id):
    url = f"{WS_ROOT}editorial/get"
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    query = {
        'id': id
    }
    resp = requests.post(url, auth=(AUTH_USER,AUTH_SECRET), headers=headers, data=query)

    if resp.ok:
        return resp.json()
    raise Exception(f"Nothing returned for {id}")

def delete(id, comment=None): # this just doesn't work. it errors 404 for IDs other than what get passed in!
    url = f"{WS_ROOT}editorial/delete_asset"
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    query = {
        'id': id,
        'user': 'joegermuska@northwestern.edu'
    }
    if comment:
        query['comment'] = comment
    resp = requests.post(url, auth=(AUTH_USER,AUTH_SECRET), headers=headers, data=query)
    if not resp.ok:
        print(f"[{resp.status_code}] error deleting {id}")
        print(resp.text)
    return resp.status_code
    

def review():
    items = [i for i in json.load(open('search.json')) if i['type'] == 'article']
    os.makedirs('review', exist_ok=True)
    ok = missing = 0
    for i in items:
        detail = get(i['id'])
        if detail['relationships']['child']:
            ok = ok + 1
        else:
            json.dump(detail,open(f"{i['id']}.json",'w'), indent=2)
            missing = missing + 1
    print("done")
    print(f"ok: {ok}")
    print(f"missing: {missing}")
    print(f"total: {len(items)}")

if __name__ == '__main__':
    # items = search()
    # json.dump(items,open('search.json', 'w'), indent=2)
    # print(f"dumped {len(items)} to search.json")
    # review()
    pass 
