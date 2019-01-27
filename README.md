[![PyPI version](https://badge.fury.io/py/txbillsearch.svg)](https://pypi.org/project/txbillsearch/)
![Python 3](https://img.shields.io/pypi/pyversions/txbillsearch.svg)

A thin, incomplete Python 3 library wrapper around the [Texas Legislature Online
Bill Search](https://capitol.texas.gov/Search/BillSearch.aspx).

## Install and Test

```bash
$ pip install txbillsearch
...
$ python -m txbillsearch
3 bills found...
result 1 of 3: HB 20 by Capriglione H Filed 2019-01-24
result 2 of 3: HB 1096 by Capriglione H Filed 2019-01-25
result 3 of 3: HJR 10 by Capriglione H Filed 2019-01-24
The next page of results is None
$
```

## Usage

```python
import txbillsearch

capriglione_finance = 'https://capitol.texas.gov/Search/BillSearch.aspx?NSP=3&SPL=True&SPC=False&SPA=True&SPS=True&Leg=86&Sess=R&ChamberH=True&ChamberS=True&BillType=B;JR;CR;R;;;&AuthorCode=A2345&SponsorCode=&ASAndOr=O&IsPA=True&IsJA=False&IsCA=False&IsPS=True&IsJS=False&IsCS=False&CmteCode=&CmteStatus=&OnDate=&FromDate=&ToDate=&FromTime=&ToTime=&LastAction=False&Actions=H001;S001;&AAO=O&Subjects=I0747;I0748;&SAO=O&TT=&ID=abcDEFghi'

search = txbillsearch.Search(capriglione_finance)

for index, bill in enumerate(search.results):
    print(f'result {index+1} of {search.result_count}: {bill}')
```

## Technical Details

For some reason,
[BillSearchResults.aspx](https://capitol.texas.gov/Search/BillSearchResults.aspx)
requires that you supply an ID, generated on
[BillSearch.aspx](https://capitol.texas.gov/Search/BillSearch.aspx). This ID
must be "fresh"; that is it must have been generated less than 24-ish hours ago
(I don't know the exact time interval). Without a "fresh" ID,
BillSearchResults.aspx displays "No bills were found matching the entered
search criteria." or redirects the client back to BillSearch.aspx.  The ID is associated with the search criteria you supply on BillSearch.aspx, so it cannot be reused with other searches on BillSearchResults.aspx alone.


This ID is generated during the ASP.NET
POSTback that occurs to BillSearch.aspx after you have selected your search
criteria, but before you are redirected to BillSearchResults.aspx:

![bill search sequence diagram](Doc/sequencediagram.png)

## Disclaimer

I made my best effort to read through the Texas Legislature Online Terms and
Conditions, and found nothing that prohibited or discouraged
automated/programmatic use or access of this information for personal and/or
non-commercial use. The [FTP site](https://capitol.texas.gov/billlookup/filedownloads.aspx) is no substitute
for a modern web service. If there's a better way to do this (e.g., a *real*
web service) I'd love to know about it, and would much prefer to use it to the
wasteful and inconvenient method developed herein.
