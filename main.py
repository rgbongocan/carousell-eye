from bs4 import BeautifulSoup
from datetime import timedelta
from requests.exceptions import RequestException, Timeout
from pprint import PrettyPrinter
from telegram.error import TelegramError, TimedOut, NetworkError
from typing import Any, Dict, List

import logging
import random
import re
import redis
import requests
import telegram
import yaml

from search import CarousellCategories, CarousellSearch, CarousellListing

config = yaml.safe_load(open("config.yaml"))
BOT = telegram.Bot(config["telegram"]["bot"]["token"])
CHANNEL = config["telegram"]["channel"]
BRANDS = config["listing"]["brands"]
RECENCY = config["listing"]["recency"]  # maximum age (in days) of listing allowed
TTL = 60 * 60 * 24 * config["listing"]["ttl"]  # expiry (in days) of listing redis entry (interpreted as "message already sent")

TITLE_LIMIT = config["message"]["limit"]["title"]
DESCRIPTION_LIMIT = config["message"]["limit"]["title"]

cache = redis.Redis(host='redis', port=6379)


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


def run_script(dry_run=True):
    # TODO: proper logging
    for brand in random.sample(BRANDS, 3):
        search = CarousellSearch(brand).filter(collections=CarousellCategories.ALL_MENS_FASHION)
        listings: List[CarousellListing] = search.execute()
        unfiltered_len = len(listings)
        listings = CarousellListing.filter_recent(listings, timedelta(days=RECENCY))
        print(f"Got {unfiltered_len} listings under {brand}; {len(listings)} are recent")
        for listing in listings:
            if cache.exists(listing.id):
                print(f"Already sent: {listing.id} - {listing.title}")
                continue
            if dry_run:
                print(f"Will send {listing.id} - {listing.title}")
                continue
            message = generate_message(listing)
            try:
                tg_message = None
                if (url := listing.photo_url):
                    tg_message: telegram.Message = BOT.send_photo(
                        CHANNEL,
                        url,
                        caption=message,
                        parse_mode=telegram.ParseMode.HTML,
                    )
                else:
                    tg_message: telegram.Message = BOT.send_message(
                        chat_id=CHANNEL,
                        text=message, 
                        parse_mode=telegram.ParseMode.HTML,
                    )
                if tg_message:
                    print(f"Successfully sent: {listing.id} - {listing.title}")
                    cache.setex(listing.id, TTL, "")
            except (TimedOut, NetworkError, TelegramError) as e:
                # TODO: Implement a retry mechanism that doesnt accidentally send dupes
                print(e)


if __name__ == "__main__":
    run_script(dry_run=False)
