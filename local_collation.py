import json
import urllib.request
from django.conf import settings as django_settings


class LocalCollation:

    def do_collate(self, data, options):
        """
        Alternative collation function to call CollateX Java microservice
        with endpoint set in environment variable COLLATEX_URL.
        """
        if 'algorithm' in options:
            # examples include 'needleman-wunsch'#'dekker'#'dekker-experimental'
            data['algorithm'] = options['algorithm']
        if 'tokenComparator' in options:
            # examples include {"type": "levenshtein", "distance": 2}#{'type': 'equality'}
            data['tokenComparator'] = options['tokenComparator']

        target = django_settings.COLLATEX_URL

        json_witnesses = json.dumps(data)
        accept_header = "application/json"

        req = urllib.request.Request(target)
        req.add_header('content-type', 'application/json')
        req.add_header('Accept', accept_header)

        response = urllib.request.urlopen(req, json_witnesses.encode('utf-8'))
        return response.read()
