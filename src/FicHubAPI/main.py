from __future__ import annotations

__version__ = (0, 0, 1)

from enum import Enum
from io import BytesIO

import requests
import json


class APIResponseTypes(Enum):
    GETFICDATA = 1
    DOWNLOADEPUB = 2
    DOWNLOADHTML = 3
    DOWNLOADMOBI = 4
    DOWNLOADPDF = 5
    ERROR = 6


class FicHubFileTypes(Enum):
    EPUB = 'epub_url'
    HTML = 'html_url'
    MOBI = 'mobi_url'
    PDF = 'pdf_url'


class FicHubAPI:
    # TODO: DOCUMENT. DOCUMENT. DOCUMENT.
    DEFAULTS = {
        'User-Agent': 'FicHubAPI/v%d.%d.%d' % __version__,
        'APIAddress': 'https://fichub.net/api/v0/epub?q=',
        'timeout': (6.1, 300)
    }

    def __init__(self, user_agent: str = None, api_address: str = None, timeout: (float, int) = None):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': user_agent or self.DEFAULTS['User-Agent']
        })

        self.api_address = api_address or self.DEFAULTS['APIAddress']
        self.timeout = timeout or self.DEFAULTS['timeout']

        self._last_response = None
        self._last_response_type = None

        self.last_fic_data = None
        self.last_fic_url = None

    def get_fic_info(self, fic_url: str = None) -> str:
        if fic_url != self.last_fic_url:
            self.get_fic_data(fic_url)
        return self.last_fic_data["info"]

    def get_fic_data(self, fic_url: str) -> dict:
        query_url = self.api_address + fic_url

        self._last_response = self.session.get(query_url)

        good_response, status_code = self.check_good_response(APIResponseTypes.GETFICDATA)
        if good_response:
            self.last_fic_data = json.loads(self._last_response.content.decode("UTF-8"))
            self.last_fic_url = fic_url
            return self.last_fic_data

        raise RuntimeError('Failed to get fic data. Status Code: ' + str(status_code))

    def download_ebook(self, file_format: str = FicHubFileTypes.EPUB.value, fic_url: str = None) -> BytesIO | None:
        if self.last_fic_data is None or self._last_response_type is APIResponseTypes.ERROR:
            if fic_url is None:
                raise RuntimeError("fic_url not set with no fic data in cache")

            self.get_fic_data(fic_url)

        # To get the cache, should I use self.last_fic_data['urls'][file_format] instead? It self-documents a bit easier
        # but it's an extra dict call.
        ebook_url = self.last_fic_data[file_format]

        self._last_response = self.session.get("https://fichub.net" + ebook_url,
                                               allow_redirects=True, timeout=self.DEFAULTS['timeout'])

        # TODO: Add dict lookup for response type
        good_response, status_code = self.check_good_response(APIResponseTypes.DOWNLOADEPUB)
        if good_response:
            return BytesIO(self._last_response.content)

        raise RuntimeError('Failed to download book. Status Code: ' + str(status_code))

    def check_good_response(self, response_type: APIResponseTypes) -> (bool, int):
        if self._last_response.status_code == 200:
            self._last_response_type = response_type
            return True, 200
        self._last_response_type = APIResponseTypes.ERROR
        return False, self._last_response.status_code

    # Should new requests go through this wrapper function?
    def new_request(self, *args, expected_response_type: APIResponseTypes = None, **kwargs):
        self._last_response = self.session.get(*args, **kwargs)
        self._last_response_type = expected_response_type if self._last_response.status_code == 200 \
            else APIResponseTypes.ERROR
