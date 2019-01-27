import sys
import logging

from .txbillsearch import Search

logging.basicConfig(level=logging.INFO)

capriglione_finance = 'https://capitol.texas.gov/Search/BillSearch.aspx?NSP=3&SPL=True&SPC=False&SPA=True&SPS=True&Leg=86&Sess=R&ChamberH=True&ChamberS=True&BillType=B;JR;CR;R;;;&AuthorCode=A2345&SponsorCode=&ASAndOr=O&IsPA=True&IsJA=False&IsCA=False&IsPS=True&IsJS=False&IsCS=False&CmteCode=&CmteStatus=&OnDate=&FromDate=&ToDate=&FromTime=&ToTime=&LastAction=False&Actions=H001;S001;&AAO=O&Subjects=I0747;I0748;&SAO=O&TT=&ID=cMVddWbvD'
author_canales = 'https://capitol.texas.gov/Search/BillSearchResults.aspx?NSP=1&SPL=True&SPC=False&SPA=False&SPS=False&Leg=86&Sess=R&ChamberH=True&ChamberS=True&BillType=B;JR;;;;;&AuthorCode=A2340&SponsorCode=&ASAndOr=O&IsPA=True&IsJA=False&IsCA=False&IsPS=True&IsJS=False&IsCS=False&CmteCode=&CmteStatus=&OnDate=&FromDate=&ToDate=&FromTime=&ToTime=&LastAction=False&Actions=&AAO=&Subjects=&SAO=&TT=&ID=rRVjTy3oj'

if len(sys.argv) > 1:
    uri = sys.argv[1]
else:
    uri = capriglione_finance

search = Search(uri)

# This is just a very simple demonstration that we can actually get 
# search results directly from BillSearchResults.aspx.
print('{} bills found...'.format(search.result_count))
for index, bill in enumerate(search.results):
    if index > 48:
        # Be nice.  Don't make gratuitous requests.
        break

    print(f'result {index+1} of {search.result_count}: {bill}')

print('The next page of results is {}'.format(
    search.page_seq.last_loaded_page.next_page_query))
