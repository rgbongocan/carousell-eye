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

from search import CarousellCategories, CarousellSearch, CarousellListing

config = yaml.safe_load(open("config.yaml"))
BOT = telegram.Bot(config["telegram"]["bot"]["token"])
CHANNEL = config["telegram"]["channel"]

TITLE_LIMIT = 30
DESCRIPTION_LIMIT = 60

def generate_message(listing: CarousellListing) -> str:
    # assume the listing is valid
    title = t if len((t := listing.title)) < TITLE_LIMIT else f"{t[:TITLE_LIMIT].strip()}..."
    description = d if len((d := listing.description)) else f"{d[:DESCRIPTION_LIMIT].strip()}..."
    message = f"<a href=\"{listing.url}\">{title.title()}</a>"
    message += f"\n{listing.price}"
    if listing.others:
        others = "\n".join(listing.others)
        message += f"\n{others}"
    message += f"\n<i>{description}</i>"
    return message


def run_script():
    # logging.basicConfig(level = logging.INFO)
    # search = CarousellSearch("Maison Kitsune").filter(collections=CarousellCategories.ALL_MENS_FASHION)
    # search = CarousellSearch("Kate Spade sling").filter(collections=CarousellCategories.WOMENS_BAG_AND_WALLETS)
    for brand in ["Bellroy"]:
        search = CarousellSearch(brand)
        listings = search.execute()
        # print(listings)
        for idx, listing in enumerate(listings):
            if idx > 5:
                break
            message = generate_message(listing)
            try:
                if (url := listing.photo_url):
                    BOT.send_photo(
                        CHANNEL,
                        url,
                        caption=message,
                        parse_mode=telegram.ParseMode.HTML,
                    )
                else:
                    BOT.send_message(
                        chat_id=CHANNEL,
                        text=message, 
                        parse_mode=telegram.ParseMode.HTML,
                    )
                print(f"Sent message for listing {listing.id}: {listing.title}")
            except (TimedOut, NetworkError, TelegramError) as e:
                # TODO: Implement a retry mechanism that doesnt accidentally send dupes
                print(e)


if __name__ == "__main__":
    run_script()
