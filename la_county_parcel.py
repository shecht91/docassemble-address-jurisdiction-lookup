"""Los Angeles County parcel lookup, for addresses the Census geocoder puts in Los Angeles County.

``la_county_lookup(street, city, zip_code)`` geocodes the address with the county's CAMS locator,
takes the first candidate scoring 98 or more, works out the parcel number (AIN) and asks the
Assessor's parcel detail API for the year built of each structure and the use type.
"""
import requests

__all__ = ['la_county_lookup', 'la_county_geocode', 'la_county_parcel_detail']

GEOCODE_URL = 'https://geocode.gis.lacounty.gov/geocode/rest/services/CAMS_Locator/GeocodeServer/findAddressCandidates'
PARCEL_URL = 'https://portal.assessor.lacounty.gov/api/parceldetail'
MIN_SCORE = 98


def la_county_geocode(address, timeout=15):
    """Return (apn, matched address) for the first candidate with a score of MIN_SCORE or more."""
    _resp = requests.get(
        GEOCODE_URL,
        params={'SingleLine': address, 'outFields': '*', 'matchOutOfRange': 'true',
                'returnMatchNarrative': 'true', 'comprehensiveZoneMatch': 'true', 'f': 'json'},
        timeout=timeout)
    if _resp.status_code != 200:
        raise Exception('County geocoder: HTTP ' + str(_resp.status_code))
    for _cand in _resp.json().get('candidates', []):
        _attrs = _cand.get('attributes') or {}
        if (_cand.get('score') or _attrs.get('Score') or 0) < MIN_SCORE:
            continue
        _type = _attrs.get('Addr_type')
        if _type == 'Parcel':
            _apn = (_attrs.get('ShortLabel') or '').strip()
        elif _type == 'PointAddress':
            _apn = (_attrs.get('AIN') or '').strip()
        else:
            continue
        if _apn:
            return _apn, _attrs.get('Match_addr') or _cand.get('address')
    raise Exception('The county geocoder found no parcel match with a score of ' + str(MIN_SCORE) + ' or more')


def la_county_parcel_detail(apn, timeout=15):
    """Return {'use_type', 'structures': [{'subpart', 'year_built', ...}], ...} for a parcel."""
    _resp = requests.get(PARCEL_URL, params={'AIN': apn}, timeout=timeout)
    if _resp.status_code != 200:
        raise Exception('Assessor: HTTP ' + str(_resp.status_code))
    _parcel = _resp.json().get('Parcel')
    if not _parcel:
        raise Exception('The Assessor returned no parcel for ' + str(apn))
    _structures = []
    for _sub in _parcel.get('SubParts') or []:
        _structures.append({'subpart': _sub.get('SubPartNumber'), 'year_built': _sub.get('YearBuilt'),
                            'units': _sub.get('NumOfUnits'), 'design_type': _sub.get('DesignType2ndDigit')})
    if not _structures and _parcel.get('YearBuilt'):
        _structures.append({'subpart': None, 'year_built': _parcel.get('YearBuilt'),
                            'units': _parcel.get('NumOfUnits'), 'design_type': None})
    return {'use_type': _parcel.get('UseType'), 'structures': _structures,
            'situs': ' '.join(str(_parcel.get(_k) or '') for _k in ('SitusStreet', 'SitusCity', 'SitusZipCode')).strip()}


def la_county_lookup(street, city, zip_code, state='CA'):
    result = {'apn': None, 'matched': None, 'use_type': None, 'structures': [], 'year_built': [], 'error': None}
    try:
        _address = ', '.join(_p for _p in (str(street).strip(), str(city).strip(), (str(state) + ' ' + str(zip_code)).strip()) if _p)
        result['apn'], result['matched'] = la_county_geocode(_address)
        _detail = la_county_parcel_detail(result['apn'])
        result['use_type'] = _detail['use_type']
        result['structures'] = _detail['structures']
        result['year_built'] = [_s['year_built'] for _s in _detail['structures'] if _s['year_built']]
    except Exception as _err:
        result['error'] = str(_err)
    return result
