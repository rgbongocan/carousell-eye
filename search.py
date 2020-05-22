from __future__ import annotations

from enum import Enum
from pprint import PrettyPrinter

import copy
import requests


CAROUSELL_HOST = "https://www.carousell.ph"
CAROUSELL_API = "api-service/filter/search/3.3/products/"


class CarousellCategories(Enum):
   ALL_MENS_FASHION = "3"


class CarousellListing:
    TITLE_LIMIT = 30
    DESCRIPTION_LIMIT = 60
    
    @property
    def url(self):
        return f"{CAROUSELL_HOST}/p/{self.id}" 


    def __init__(
        self,
        id=None,
        title=None,
        url=None,
        price=None,
        description=None,
        others=[],
        photo_url=None
    ) -> None:
        self.id = id
        self.title = title
        self.price = price
        self.description = description
        self.others = others,
        self.photo_url = photo_url


    # should be outside
    def generate_message(self) -> str:
        self.validate()
        title = t if len((t := self.title)) < self.TITLE_LIMIT else f"{t[:self.TITLE_LIMIT].strip()}..."
        description = "\n".join(self.description)
        if len(description) > self.DESCRIPTION_LIMIT:
            description = f"{description[:self.DESCRIPTION_LIMIT].strip()}..."

        message = f"<a href=\"{self.url}\">{title.title()}</a>"
        if self.price:
            message += f"\n{self.price}"
        message += f"\n<i>{description}</i>"
        return message


    def json(self):
        return {
            "id": self.id,
            "title": self.title,
            "price": self.price,
            "description": self.description,
            "others": self.others,
            "url": self.url,
            "photo_url": self.photo_url,
        }


    def __repr__(self):
        return str(self.json())


class CarousellSearch:
    def __init__(
        self,
        term=None,
        count=20,
        filters={}
    ):
        self.term = term
        self.count = count
        self._filters = filters


    def filter(self, **kwargs) -> CarousellSearch:
        new_filters = copy.deepcopy(self._filters)
        for k, v in kwargs.items():
            if k not in new_filters:
                new_filters[k] = []
            new_filters[k].append(v)
        return self._copy_with(
            term=self.term,
            count=self.count,
            filters=new_filters
        )


    def _copy_with(self, **kwargs) -> CarousellSearch:
        new_kwargs = dict(
            term=self.term,
            count=self.count,
            filters=self._filters,
        )
        new_kwargs.update(kwargs)
        return CarousellSearch(**new_kwargs)


    def json(self):
        params = {
            "query": self.term,
            "count": self.count,
            "filters": [],
            # TODO: parametrize? Hardcoded is Philippines, presumably
            "countryId": "1694008",
            "isFreeItems": False,
            "locale": "en",
            # TODO: parametrize? Hardcoded is to sort by most recent
            "prefill": {
                "prefill_sort_by": "time_created,descending"
            },
            "sortParam": {
                "fieldName": "time_created",
                "ascending": {
                    "value": False
                }
            }
        }
        for k, v in self._filters.items():
            # this is how the carousell API expects it
            params["filters"].append({
                "fieldName": k,
                "idsOrKeywords": {
                    "value": v
                }
            })

        return params

    
    def __repr__(self):
        return str(self.json())


    def execute(self) -> List[CarousellListing]:
        # turn into a generator instead?
        listings: List[CarousellListing] = []
        resp = requests.post(f"{CAROUSELL_HOST}/{CAROUSELL_API}", json=self.json())
        results = resp.json()["data"]["results"]
        for lc in [r["listingCard"] for r in results]:
            kwargs = {
                "id": lc["id"],
                "others": []
            }
            for component in lc["belowFold"]:
                if (name := component["component"]) == "header_1":
                    key = "title"
                elif name == "header_2":
                    key = "price"
                elif name == "paragraph":
                    if "description" not in kwargs:
                        key = "description"
                    else:
                        key = "others"
                
                content = component["stringContent"]
                if key == "others":
                    if content:
                        kwargs[key].append(content)
                else:
                    kwargs[key] = content  
            if lc["media"]:
                kwargs["photo_url"] = lc["media"][0].get("photoItem", {}).get("url")
            listings.append(CarousellListing(**kwargs))
        return listings
