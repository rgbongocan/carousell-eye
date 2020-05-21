from bs4 import BeautifulSoup
from requests.exceptions import Timeout
from pprint import PrettyPrinter
from typing import Any, Dict, List

import re
import requests
import telegram
import yaml


config = yaml.safe_load(open("config.yaml"))
CAROUSELL_HOST = config["carousell"]["host"]
CAROUSELL_URL = f"{CAROUSELL_HOST}/categories/" \
    "mens-fashion-3?" \
    "search={search}" \
    "&sort_by=time_created%2Cdescending"
BOT = telegram.Bot(config["telegram"]["bot"]["token"])
CHANNEL = config["telegram"]["channel"]


def cut_readable(s: str) -> str:
    pass


def get_listing_photo(url: str, title: str) -> str:
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text, "html.parser")
    imgs = soup.find_all("img", title=title)
    if not imgs:
        return None
    return imgs[-1].get("src")


LISTING_REGEXP = "^/p/"
LISTING_CURRENCY = "PHP"
LISTING_SIZE_PREFIX = "Size:"


def get_listings(brand: str) -> List[Any]: 
    url = CAROUSELL_URL.format(search=brand.replace("20%"," "))
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text, "html.parser")

    
    listings = [] 
    for listing_node in soup.find_all("a", href=re.compile(LISTING_REGEXP)):
        listing = {
            "title": None,
            "link": f"{CAROUSELL_HOST}{listing_node.get('href')}",
            "price": None,
            "size": None,
            # as of writing, this will contain a listing's description on Carousell 
            # and possibly other <p> nodes we might not recognize in the future 
            "description": [] 
        }

        for p_idx, p in enumerate(listing_node.find_all("p", recursive=False)):
            if not (listing_info := p.string):
                continue

            key = "description"
            if p_idx == 0:
                key = "title"
                # TODO: cut title into a readable string            
            elif listing_info.startswith(LISTING_CURRENCY):
                key = "price"
            elif listing_info.startswith(LISTING_SIZE_PREFIX):
                key = "size"
            
            if key == "description":
                listing[key].append(listing_info)
            else:
                listing[key] = listing_info

        listings.append(listing)

    return listings        
    
            # if (info := p.string):
            #     is_title = info_idx == 0  # presumably, anyway
            #     if is_title:
            #         listing_title = info
            #     limit = 30 if is_title else 60
            #     if len(info) > limit:
            #         info = f"{info[:limit]}..."
            #     if is_title:
            #         # presumably the title
            #         info = f"<a href=\"{listing_link}\">{info}</a>"
            #     else:
            #         if not info.startswith("PHP") and not info.startswith("Size:"):
            #             info = f"<i>{info}</i>"
            #     infos.append(info)
        # listing_photo = get_listing_photo(listing_link, listing_title)
        # formatted_message = "\n".join(infos)
        # if not dry_run and listing_idx < 2:
        #     if listing_photo:
        #         try:
        #             BOT.send_photo(
        #                 CHANNEL,
        #                 listing_photo,
        #                 caption=formatted_message,
        #                 parse_mode=telegram.ParseMode.HTML,
        #             )
        #         except Timeout:
        #             BOT.send_message(
        #                 CHANNEL,
        #                 text=formatted_message, 
        #                 parse_mode=telegram.ParseMode.HTML,
        #             )
        #         # need to guard againts telegram's flood control
        #     else:
        #         BOT.send_message(
        #             chat_id=CHANNEL,
        #             text=formatted_message, 
        #             parse_mode=telegram.ParseMode.HTML,
        #         )

TITLE_LIMIT = 30
DESCRIPTION_LIMIT = 60

def format_message(listing: Dict[str, Any]) -> str:
    title = t if len(t := listing["title"]) < TITLE_LIMIT else f"{t[:TITLE_LIMIT].strip()}..."
    description = "\n".join([
        d if len(d) > DESCRIPTION_LIMIT else f"{d[:DESCRIPTION_LIMIT].strip()}..."
        for d in listing["description"]
    ])

    return f"""
<a href="{listing["link"]}">{title.title()}</a>
{listing["price"]}
{listing["size"]}
<i>{description}</i>"""


if __name__ == "__main__":
    for brand in {"APC", "Comme des Garcons", "Visvim"}:
        listings = get_listings(brand)
        for idx, listing in enumerate(listings):
            if idx > 3:
                break
            photo_url = get_listing_photo(listing["link"], listing["title"])
            message = format_message(listing)
            print(message, photo_url)
            if photo_url:
                BOT.send_photo(
                    CHANNEL,
                    photo_url,
                    caption=message,
                    parse_mode=telegram.ParseMode.HTML,
                )
            else:
                BOT.send_message(
                    chat_id=CHANNEL,
                    text=message, 
                    parse_mode=telegram.ParseMode.HTML,
                )