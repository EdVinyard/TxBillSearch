import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
import threading

from page import Page, PageSequence, SearchResults

TRACE = False

if TRACE:
    from pprint import pprint

BILL_SEARCH_URI = "https://capitol.texas.gov/Search/BillSearch.aspx"
VIEWSTATE_ID = '__VIEWSTATE'
PREVPAGE_ID = '__PREVIOUSPAGE'
BILL_SEARCH_POSTBACK_PARAMS = {
    "__EVENTTARGET": "",
    "__EVENTARGUMENT": "",
    "__LASTFOCUS": "",
    ## "__VIEWSTATE": extracted from cold response
    ## "__PREVIOUSPAGE": extracted from cold response
    "cboLegSess": "86R",
    "chkHouse": "on",
    "chkSenate": "on",
    "chkB": "on",
    "chkJR": "on",
    "btnSearch": "Search",
    "usrLegislatorsFolder$cboAuthor": "",
    "usrLegislatorsFolder$chkPrimaryAuthor": "on",
    "usrLegislatorsFolder$authspon": "rdoOr",
    "usrLegislatorsFolder$cboSponsor": "",
    "usrLegislatorsFolder$chkPrimarySponsor": "on",
    "usrSubjectsFolder$subjectandor": "rdoOr",
    "usrSubjectsFolder$txtCodes": "",
    "usrCommitteesFolder$cboCommittee": "",
    "usrCommitteesFolder$status": "rdoStatusBoth",
    "usrActionsFolder$actionandor": "rdoOr",
    "usrActionsFolder$txtCodes": "",
    "usrActionsFolder$lastaction": "rdoLastActionNo",
    "usrActionsFolder$dtActionOnDate": "",
    "usrActionsFolder$dtActionFromDate": "",
    "usrActionsFolder$dtActionToDate": "",
    }
BILL_SEARCH_RESULT_URI = ('https://capitol.texas.gov/Search/BillSearchResults.aspx' +
    '?NSP=1' + 
    '&SPL=False' + 
    '&SPC=False' + 
    '&SPA=False' + 
    '&SPS=True' + 
    '&Leg=86' + 
    '&Sess=R' + 
    '&ChamberH=True' + 
    '&ChamberS=True' + 
    '&BillType=B;JR;;;;;' + 
    '&AuthorCode=' + 
    '&SponsorCode=' + 
    '&ASAndOr=O' + 
    '&IsPA=True' + 
    '&IsJA=False' + 
    '&IsCA=False' + 
    '&IsPS=True' + 
    '&IsJS=False' + 
    '&IsCS=False' + 
    '&CmteCode=' + 
    '&CmteStatus=' + 
    '&OnDate=' + 
    '&FromDate=' + 
    '&ToDate=' + 
    '&FromTime=' + 
    '&ToTime=' + 
    '&LastAction=False' + 
    '&Actions=' + 
    '&AAO=' + 
    '&Subjects=I0320;I0013;I0760;I0755;I0002;S0443;S0367;S0496;I0875;I0885;I0870;' + 
    '&SAO=O' + 
    '&TT=')
    # '&ID=s36alcgKa' add the ID query param in dynamically, later

RESULT_COUNT_11_URI = 'https://capitol.texas.gov/Search/BillSearchResults.aspx?NSP=2&SPL=True&SPC=False&SPA=True&SPS=False&Leg=86&Sess=R&ChamberH=True&ChamberS=True&BillType=B;JR;;;;;&AuthorCode=A2100&SponsorCode=&ASAndOr=O&IsPA=True&IsJA=False&IsCA=False&IsPS=True&IsJS=False&IsCS=False&CmteCode=&CmteStatus=&OnDate=&FromDate=11/1/2018&ToDate=1/1/2019&FromTime=&ToTime=&LastAction=False&Actions=H001;&AAO=O&Subjects=&SAO=&TT='
RESULT_COUNT_820_URI = 'https://capitol.texas.gov/Search/BillSearchResults.aspx?NSP=1&SPL=False&SPC=False&SPA=True&SPS=False&Leg=86&Sess=R&ChamberH=True&ChamberS=True&BillType=B;JR;;;;;&AuthorCode=&SponsorCode=&ASAndOr=O&IsPA=True&IsJA=False&IsCA=False&IsPS=True&IsJS=False&IsCS=False&CmteCode=&CmteStatus=&OnDate=&FromDate=&ToDate=&FromTime=&ToTime=&LastAction=False&Actions=H001;&AAO=O&Subjects=&SAO=&TT='

def hidden_input_value(soup, id):
    return soup \
        .find(name='input', attrs={'type':'hidden','id':id}) \
        .attrs['value']


def search_id(bill_search_redirect_uri):
    '''
    Returns only the ID, given a redirect URI from BillSearch.aspx like

        /Search/BillSearchResults.aspx?NSP=1&SPL=False& ... &ID=BMI3UVlA2

    '''
    parsed = urlparse(bill_search_redirect_uri)
    query_params = parse_qs(parsed.query)
    id_values = query_params['ID']
    return id_values[0]


def postback_data(cold_response):
    ## Prepare the POSTBACK to BillSearch.aspx.
    soup = BeautifulSoup(cold_response.text, 'html.parser')
    post_data = BILL_SEARCH_POSTBACK_PARAMS.copy()
    post_data[VIEWSTATE_ID] = hidden_input_value(soup, VIEWSTATE_ID)
    post_data[PREVPAGE_ID]  = hidden_input_value(soup, PREVPAGE_ID)
    
    if TRACE: pprint(post_data)
    
    return post_data


def new_search_id(session):
    cold_response = session.get(BILL_SEARCH_URI)
    postback_response = session.post(
        BILL_SEARCH_URI, 
        data=postback_data(cold_response), 
        allow_redirects=False) # <== This parameter is critical!
    redirect_uri = postback_response.headers.get('Location', None)

    if postback_response.status_code != 302 or redirect_uri is None:
        raise RuntimeError("Failed to trick BillSearch.aspx into issuing a fresh search ID.")

    id = search_id(redirect_uri)
    return id


if __name__ == '__main__':
    session = requests.Session()

    def http_get(uri):
        r = session.get(uri, allow_redirects=False)

        if r.status_code != 200:
            raise RuntimeError(
                'Unexpected response HTTP status {} while fetching {}'.format(
                    r.status_code,
                    uri))

        return r.text

    id = new_search_id(session)     # <== THE IMPORTANT PART!
    # Substitute this "fresh" ID for the one included in old searches.

    results_uri = RESULT_COUNT_820_URI + '&ID=' + id
    first_page = Page(http_get(results_uri), results_uri)
    page_seq = PageSequence(http_get, first_page)
    search_results = SearchResults(page_seq)

    print('{} bills found...'.format(search_results.count))
    for index, bill in enumerate(search_results.bills):
        if index > 73:
            break

        print(bill)


## TODO: encapsulate most of this module into a stateful class
## TODO: lazily iterate over the paged search results
