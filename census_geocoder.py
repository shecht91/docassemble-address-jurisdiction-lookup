"""Find the city and county of an address with the US Census Bureau geocoder.

``lookup(street, city, zip_code)`` returns a dict shaped like the one in cdtfa_lookup.py, so the
two services can be swapped in the interview.
"""
import re

import requests

__all__ = ['census_lookup']

CENSUS_URL = 'https://geocoding.geo.census.gov/geocoder/geographies/onelineaddress'


def _first_basename(geographies, layer):
    for _item in geographies.get(layer) or []:
        _name = (_item.get('BASENAME') or '').strip()
        if _name:
            return _name
    return ''


def census_lookup(street, city, zip_code, state='CA', timeout=15):
    """Look up an address. The city is the BASENAME of the Incorporated Place, or
    ``Unincorporated <county basename>`` when the address is in no incorporated place."""
    result = {'city': None, 'county': None, 'error': None, 'confidence': None, 'matched': None,
              'candidates': [], 'notes': []}
    try:
        _address = ', '.join(str(_p).strip() for _p in (street, city, ' '.join(str(_p).strip() for _p in (state, zip_code) if _p)) if _p)
        _resp = requests.get(
            CENSUS_URL,
            params={'address': _address, 'benchmark': 4, 'vintage': 4, 'format': 'json', 'layers': '28,82'},
            timeout=timeout)
        if _resp.status_code != 200:
            raise Exception('HTTP ' + str(_resp.status_code))
        _matches = _resp.json()['result']['addressMatches']
        if not _matches:
            raise Exception('The Census geocoder found no match for that address')
        _seen = []
        for _match in _matches:
            _geo = _match.get('geographies') or {}
            _county = _first_basename(_geo, 'Counties')
            if not _county:
                continue
            _place = _first_basename(_geo, 'Incorporated Places') or ('Unincorporated ' + _county)
            if (_place, _county) not in _seen:
                _seen.append((_place, _county))
                result['candidates'].append({'city': _place, 'county': _county})
        if not result['candidates']:
            raise Exception('The Census geocoder did not return a county for that address')
        result['city'] = result['candidates'][0]['city']
        result['county'] = result['candidates'][0]['county']
        result['matched'] = _matches[0].get('matchedAddress')
        # The service returns its own best match. Say so when that match is not what was typed.
        _matched_zip = re.findall(r'(?<![0-9])[0-9]{5}(?![0-9])', result['matched'] or '')
        if _matched_zip and zip_code and _matched_zip[-1] != str(zip_code).strip()[:5]:
            result['notes'].append('The matched zip code is **' + _matched_zip[-1] + '**, not the **' + str(zip_code).strip()[:5] + '** you entered.')
    except Exception as _err:
        result['error'] = str(_err)
    return result
