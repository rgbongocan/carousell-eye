from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum
from time import time
from typing import Any, Dict, List

import copy
import requests


CAROUSELL_HOST = "https://www.carousell.ph"
CAROUSELL_API = "api-service/filter/search/3.3/products/"


class CarousellCategories(Enum):
    ALL_MENS_FASHION = "3"
    WOMENS_BAG_AND_WALLETS = "844"


class CarousellListing:
    def __init__(
        self,
        id=None,
        created_at=None,
        title=None,
        url=None,
        price=None,
        description=None,
        others=[],
        photo_url=None,
    ) -> None:
        self.id = id
        self.created_at = created_at
        self.title = title
        self.price = price
        self.description = description
        self.others = others
        self.photo_url = photo_url

    @property
    def url(self) -> str:
        return f"{CAROUSELL_HOST}/p/{self.id}"

    def json(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "created_at": self.created_at,
            "title": self.title,
            "price": self.price,
            "description": self.description,
            "others": self.others,
            "url": self.url,
            "photo_url": self.photo_url,
        }

    def __repr__(self) -> str:
        return str(self.json())

    @staticmethod
    def filter_recent(
        listings: List[CarousellListing], age_lte: timedelta
    ) -> List[CarousellListing]:
        """
        Filter listings in-python with max age allowed specified by timedelta
        """
        return [
            listing
            for listing in listings
            if (datetime.now() - listing.created_at <= age_lte)
        ]


class CarousellSearch:
    def __init__(self, term=None, count=20, filters={}):
        self.term = term
        self.count = count
        self._filters = filters

    def filter(self, **kwargs) -> CarousellSearch:
        new_filters = copy.deepcopy(self._filters)
        for k, v in kwargs.items():
            if k not in new_filters:
                new_filters[k] = []
            new_filters[k].append(v.value if isinstance(v, Enum) else v)
        return self._copy_with(term=self.term, count=self.count, filters=new_filters)

    def _copy_with(self, **kwargs) -> CarousellSearch:
        new_kwargs = dict(term=self.term, count=self.count, filters=self._filters,)
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
            "prefill": {"prefill_sort_by": "time_created,descending"},
            "sortParam": {"fieldName": "time_created", "ascending": {"value": False}},
        }
        for k, v in self._filters.items():
            # this is how the carousell API expects it
            params["filters"].append({"fieldName": k, "idsOrKeywords": {"value": v}})

        return params

    def __repr__(self) -> str:
        return str(self.json())

    def execute(self) -> List[CarousellListing]:
        # turn into a generator instead?
        listings: List[CarousellListing] = []
        resp = requests.post(f"{CAROUSELL_HOST}/{CAROUSELL_API}", json=self.json())
        results = resp.json()["data"].get("results", [])
        for lc in [r["listingCard"] for r in results]:
            ts_component = next(
                (c for c in lc["aboveFold"] if c["component"] == "time_created"), {}
            )
            ts = (
                ts_component.get("timestampContent", {})
                .get("seconds", {})
                .get("low", int(time()))
            )
            kwargs = {
                "id": lc["id"],
                "created_at": datetime.fromtimestamp(ts),
                "others": [],
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
