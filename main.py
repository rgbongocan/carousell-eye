from bs4 import BeautifulSoup
from requests.exceptions import Timeout
from typing import Any, List

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


def get_listings(brand: str, dry_run=True) -> List[Any]: 
    url = CAROUSELL_URL.format(search=brand.replace("20%"," "))
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text, "html.parser")

    for listing_idx, listing_node in enumerate(soup.find_all("a", href=re.compile("^/p/"))):
        listing_title = None
        listing_link = f"{CAROUSELL_HOST}{listing_node.get('href')}"
        infos = []
        for info_idx, p in enumerate(listing_node.find_all("p", recursive=False)):
            if (info := p.string):
                is_title = info_idx == 0  # presumably, anyway
                if is_title:
                    listing_title = info
                limit = 30 if is_title else 60
                if len(info) > limit:
                    info = f"{info[:limit]}..."
                if is_title:
                    # presumably the title
                    info = f"<a href=\"{listing_link}\">{info}</a>"
                else:
                    if not info.startswith("PHP") and not info.startswith("Size:"):
                        info = f"<i>{info}</i>"
                infos.append(info)
        listing_photo = get_listing_photo(listing_link, listing_title)
        formatted_message = "\n".join(infos)
        if not dry_run and listing_idx < 2:
            if listing_photo:
                try:
                    BOT.send_photo(
                        CHANNEL,
                        listing_photo,
                        caption=formatted_message,
                        parse_mode=telegram.ParseMode.HTML,
                    )
                except Timeout:
                    BOT.send_message(
                        CHANNEL,
                        text=formatted_message, 
                        parse_mode=telegram.ParseMode.HTML,
                    )
                # need to guard againts telegram's flood control
            else:
                BOT.send_message(
                    chat_id=CHANNEL,
                    text=formatted_message, 
                    parse_mode=telegram.ParseMode.HTML,
                )
    return


if __name__ == "__main__":
    # print("config", config)
    print(get_listings("Visvim", dry_run=False))