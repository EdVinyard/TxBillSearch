A thin, incomplete Python library wrapper around the [Texas Legislature Online
Bill Search](https://capitol.texas.gov/Search/BillSearch.aspx).

## Install and Test

```bash
$ pip install txbillsearch
...
$ python -m txbillsearch.txbillsearch
1604 bills found...
result 1 of 1604: HB 1 by Zerwas H Filed 2019-01-23
result 2 of 1604: HB 20 by Capriglione H Filed 2019-01-24
...
result 41 of 1604: HB 59 by Swanson H Filed 2018-11-12
$
```

## Module Usage

```python
import txbillsearch

# NOTICE: We chopped off the 'ID=cMVddWbvD' query param!
SESSION_86_BILLS = 'https://capitol.texas.gov/Search/BillSearchResults.aspx?NSP=1&SPL=False&SPC=False&SPA=True&SPS=False&Leg=86&Sess=R&ChamberH=True&ChamberS=True&BillType=B;JR;CR;R;;;&AuthorCode=&SponsorCode=&ASAndOr=O&IsPA=True&IsJA=False&IsCA=False&IsPS=True&IsJS=False&IsCS=False&CmteCode=&CmteStatus=&OnDate=&FromDate=&ToDate=&FromTime=&ToTime=&LastAction=False&Actions=S000;S001;H001;&AAO=O&Subjects=&SAO=&TT=' # NO ID!

id, search_results = txbillsearch.search(SESSION_86_BILLS)

# This is just a very simple demonstration that we can actually get 
# search results directly from BillSearchResults.aspx.
print('{} bills found...'.format(search_results.count))
for index, bill in enumerate(search_results.bills):
    if index > 40:
        break

    print('result {} of {}: {}'.format(
        index+1, 
        search_results.count, 
        bill))
```

## Technical Details

For some reason,
[BillSearchResults.aspx](https://capitol.texas.gov/Search/BillSearchResults.aspx)
requires that you supply an ID, generated on
[BillSearch.aspx](https://capitol.texas.gov/Search/BillSearch.aspx). This ID
must be "fresh"; that is it must have been generated less than 24-ish hours ago
(I don't know the exact time interval). Without a "fresh" ID,
BillSearchResults.aspx displays "No bills were found matching the entered
search criteria." or redirects the client back to BillSearch.aspx.


This ID is generated during the ASP.NET
POSTback that occurs to BillSearch.aspx after you have selected your search
criteria, but before you are redirected to BillSearchResults.aspx:

![bill search sequence diagram](Doc/sequencediagram.png)

## Disclaimer

I made my best effort to read through the Texas Legislature Online Terms and
Conditions, and found nothing that prohibited automated/programmatic use or
access of this information. If there's a better way to do this (e.g., a *real*
web service) I'd love to know about it, and would much prefer to use it to the
wasteful and inconvenient method developed herein.
