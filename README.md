The census_geocoder takes a street address, city, and zip and searches for the geography of that address using the US Census geocoder API. 
Currently, California is hardcoded but this can be easily switched.

The address search will return a county and, if the address is in an incorporated place, an incorporated place.
If an incorporated place is not returned, then the jurisdiction is set as "Unincorporated Area of {county}".
If an incorporated place is returned, then the jurisdiction is set as that place's name.

For addresses that are found to be in the County of Los Angeles, an addition search is performed using the LA County Assessor's API
