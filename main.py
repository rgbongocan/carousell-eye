from bs4 import BeautifulSoup
from requests.exceptions import RequestException, Timeout
from pprint import PrettyPrinter
from telegram.error import TelegramError, TimedOut, NetworkError
from typing import Any, Dict, List

import logging
import re
import requests
import telegram
import yaml

from listing import CarousellListing


config = yaml.safe_load(open("config.yaml"))
CAROUSELL_HOST = config["carousell"]["host"]
CAROUSELL_URL = f"{CAROUSELL_HOST}/categories/" \
    "mens-fashion-3?" \
    "search={search}" \
    "&sort_by=time_created%2Cdescending"
BOT = telegram.Bot(config["telegram"]["bot"]["token"])
CHANNEL = config["telegram"]["channel"]


def get_listings(brand: str) -> List[Any]: 
    url = CAROUSELL_URL.format(search=brand.replace("20%"," "))
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text, "html.parser")

    listings: List[CarousellListing] = [] 
    for listing_node in soup.find_all("a", href=re.compile("^/p/")):
        listing = CarousellListing(url=f"{CAROUSELL_HOST}{listing_node.get('href')}")
        for p_idx, p in enumerate(listing_node.find_all("p", recursive=False)):
            if not (listing_info := p.string):
                continue

            key = "description"
            if p_idx == 0:
                key = "title"
            elif listing_info.startswith("PHP "):
                key = "price"
            elif listing_info.startswith("Size: "):
                key = "size"
            
            if key == "description":
                pass
                listing.description.append(listing_info)
            else:
                setattr(listing, key, listing_info)
        listings.append(listing)

    return listings        
    

if __name__ == "__main__":
    for brand in ("APC", "Commes des Garcons", "Nanamica"):
        listings = get_listings(brand)
        for idx, listing in enumerate(listings):
            # rate-limit for dev purposes
            if idx > 1:
                break
            photo_url = listing.photo_url
            message = listing.generate_message()
            # 2 send attempts per listing
            for _ in range(2):
                try:
                    if photo_url:
                        BOT.send_photo(
                            CHANNEL,
                            photo_url,
                            caption=message,
                            parse_mode=telegram.ParseMode.HTML,
                        )
                        break
                    else:
                        BOT.send_message(
                            chat_id=CHANNEL,
                            text=message, 
                            parse_mode=telegram.ParseMode.HTML,
                        )
                        break
                except (TimedOut, NetworkError):
                    # retry until we've successfully imgs or we run out of attempts   
                    pass
                except TelegramError as e:
                    # log the breaking error and move on to the next listing
                    logging.error(e)
                    break