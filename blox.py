import json
import os
import requests
from datetime import datetime, timedelta
from pathlib import Path

import logging
logger = logging.getLogger('blox')

AUTH_USER = os.environ['AUTH_USER']
AUTH_SECRET = os.environ['AUTH_SECRET']

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
        

    now = datetime.now()
    start_time = now + timedelta(days=365*100) # during testing, use a date far in the future because stories go live when this date is now or past

    data = {
        'id': f'knightlab-bot-{now.isoformat()}',
        'type': 'article',
        'title': headline,
        'byline': 'Redaccion El Vocero',
        'content': content,
        'start_time': start_time.isoformat(), # i
        'keywords': ['weatheralert'], # do they want anything here?
        'sections': ['weather'],
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
            logger.debug(f"would have posted image code: {image_code}")

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

def search(query="weather"):
    # https://www.elvocero.com/tncms/webservice/#operation/editorial_search
    url = f"{WS_ROOT}editorial/search"

    data = {
        'q': query,
        'l': 100,
        'o': 0, # eventually we'll want to paginate with l (length) and o (offset)
        'admin': True
    }

    resp = requests.get(url, data=data)
    if resp.ok:
        print(resp.text)
    else:
        print(f"Error {resp.status_code}")


if __name__ == '__main__':
    search()
