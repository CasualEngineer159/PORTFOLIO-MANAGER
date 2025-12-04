#!/usr/bin/env python3.12

# Copyright 2017 Bloomberg Finance L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import urllib.request
import urllib.parse
import os
import pandas as pd

"""
See https://www.openfigi.com/api for more information.

This script is written to be run by python3 - tested with python3.12 - without any external libraries.
For more involved use cases, consider using open source packages: https://pypi.org/
"""

JsonType = None | int | str | bool | list["JsonType"] | dict[str, "JsonType"]

OPENFIGI_API_KEY = os.environ.get(
    "OPENFIGI_API_KEY", None
)  # Put your API key here or in env var

OPENFIGI_BASE_URL = "https://api.openfigi.com"


def api_call(
    path: str,
    data: dict | None = None,
    method: str = "POST",
) -> JsonType:
    """
    Make an api call to `api.openfigi.com`.
    Uses builtin `urllib` library, end users may prefer to
    swap out this function with another library of their choice

    Args:
        path (str): API endpoint, for example "search"
        method (str, optional): HTTP request method. Defaults to "POST".
        data (dict | None, optional): HTTP request data. Defaults to None.

    Returns:
        JsonType: Response of the api call parsed as a JSON object
    """

    headers = {"Content-Type": "application/json"}
    if OPENFIGI_API_KEY:
        headers |= {"X-OPENFIGI-APIKEY": OPENFIGI_API_KEY}

    request = urllib.request.Request(
        url=urllib.parse.urljoin(OPENFIGI_BASE_URL, path),
        data=data and bytes(json.dumps(data), encoding="utf-8"),
        headers=headers,
        method=method,
    )

    with urllib.request.urlopen(request) as response:
        json_response_as_string = response.read().decode("utf-8")
        json_obj = json.loads(json_response_as_string)
        return json_obj

def venue_interpreter(venue):

    exchange_codes = pd.read_csv(
        f'DATA/EXCHANGE_CODES.csv',
        delimiter=";",
        keep_default_na=False,
    )

    mask = exchange_codes.apply(lambda radek: radek.astype(str).str.contains(venue, na=False).any(), axis=1)

    index = exchange_codes[mask].index.tolist()

    figi, yahoo = None, None

    if len(index) > 0:
        figi = exchange_codes["figi_code"].iloc[index[0]]
        yahoo = exchange_codes["yahoo_suf"].iloc[index[0]]

    return figi, yahoo

def save_figi_response(response, isin):

    file_path = f"DATA/figi.response.{isin}.json"
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(response, f, indent=4)


def load_figi_response(isin) -> dict:
    # Načte informace z JSON souboru do slovníku.
    try:
        file_path = f"DATA/figi.response.{isin}.json"
        with open(file_path, 'r', encoding='utf-8') as f:
            stock_info = json.load(f)
        return stock_info
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}


def ticker_from_isin(isin, exchange):

    mapping_response = load_figi_response(isin)

    if mapping_response == {}:

        mapping_request = [
            {"idType": "ID_ISIN", "idValue": isin},
        ]
        mapping_response = api_call("/v3/mapping", mapping_request)

        save_figi_response(mapping_response, isin)

    ticker_map = {}

    # Procházíme všechny výsledky dotazů (protože API vrací seznam)
    for job in mapping_response:
        # Kontrola, zda job obsahuje data a ne error
        if 'data' in job:
            for item in job['data']:
                exchange_code = item.get('exchCode')
                ticker = item.get('ticker')

                # Přidáme do mapy jen pokud máme obě hodnoty
                if exchange_code and ticker:
                    ticker_map[exchange_code] = ticker

    return ticker_map.get(exchange, None)