from bs4 import BeautifulSoup
from requests.exceptions import RequestException, Timeout
from typing import Any, Dict, List

import re
import requests
import yaml


class UrlRequiredException(Exception):
    pass


class TitleRequiredException(Exception):
    pass


class CarousellListing:
    MAX_HTTP_REQUESTS = 2
    TITLE_LIMIT = 30
    DESCRIPTION_LIMIT = 60
    
    title = None
    url = None
    _photo_url = None
    price = None
    size = None
    # as of writing, this will contain a listing's description on Carousell 
    # and possibly other <p> nodes' contents we might not recognize in the future 
    description = []


    def __init__(self, title=None, url=None, price=None, size=None, description=[]) -> None:
        self.title = title
        self.url = url
        self.price = price
        self.size = size
        self.description = description


    def validate(self) -> None:
        if not self.title:
            raise TitleRequiredException("Listing title is required")
        if not self.url:
            raise UrlRequiredException("Listing url is required")


    @property
    def photo_url(self) -> str:
        if not self._photo_url:
            self.validate()
            url = self.url
            title = self.title
            imgs = None
            for _ in range(self.MAX_HTTP_REQUESTS):
                try:
                    resp = requests.get(url)
                    soup = BeautifulSoup(resp.text, "html.parser")
                    imgs = soup.find_all("img", title=title)
                    break
                except RequestException:
                    # retry until soup.find_all assigns to imgs or we run out of attempts   
                    pass
            
            self._photo_url = None if not imgs else imgs[-1].get("src")
        
        return self._photo_url


    def generate_message(self) -> str:
        self.validate()
        title = t if len((t := self.title)) < self.TITLE_LIMIT else f"{t[:self.TITLE_LIMIT].strip()}..."
        description = "\n".join(self.description)
        if len(description) > self.DESCRIPTION_LIMIT:
            description = f"{description[:self.DESCRIPTION_LIMIT].strip()}..."

        return f"""
<a href="{self.url}">{title.title()}</a>
{self.price or "No price indicated"}
{self.size or "No size indicated"}
<i>{description}</i>"""

