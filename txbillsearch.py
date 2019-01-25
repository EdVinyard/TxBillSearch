import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
import threading

from page import Page, PageSequence, SearchResults

# TODO: Use logging module instead.
DEBUG = False

if DEBUG:
    from pprint import pprint

_BILL_SEARCH_URI = "https://capitol.texas.gov/Search/BillSearch.aspx"
_VIEWSTATE_ID = '__VIEWSTATE'
_PREVPAGE_ID = '__PREVIOUSPAGE'
_BILL_SEARCH_POSTBACK_PARAMS = {
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


def _hidden_input_value(soup, id):
    return soup \
        .find(name='input', attrs={'type':'hidden','id':id}) \
        .attrs['value']


def _search_id(bill_search_redirect_uri):
    '''
    Returns only the ID, given a redirect URI from BillSearch.aspx like

        /Search/BillSearchResults.aspx?NSP=1&SPL=False& ... &ID=BMI3UVlA2

    '''
    parsed = urlparse(bill_search_redirect_uri)
    query_params = parse_qs(parsed.query)
    id_values = query_params['ID']
    return id_values[0]


def _postback_data(cold_response):
    ## Prepare the POSTBACK to BillSearch.aspx.
    soup = BeautifulSoup(cold_response.text, 'html.parser')
    post_data = _BILL_SEARCH_POSTBACK_PARAMS.copy()
    post_data[_VIEWSTATE_ID] = _hidden_input_value(soup, _VIEWSTATE_ID)
    post_data[_PREVPAGE_ID]  = _hidden_input_value(soup, _PREVPAGE_ID)
    
    if DEBUG: pprint(post_data)
    
    return post_data


def _new_search_id(session):
    cold_response = session.get(_BILL_SEARCH_URI)
    postback_response = session.post(
        _BILL_SEARCH_URI, 
        data=_postback_data(cold_response), 
        allow_redirects=False) # <== This parameter is critical!
    redirect_uri = postback_response.headers.get('Location', None)

    if postback_response.status_code != 302 or redirect_uri is None:
        raise RuntimeError("Failed to trick BillSearch.aspx into issuing a fresh search ID.")

    id = _search_id(redirect_uri)
    return id


def _http_get_factory(requests_session):
    def http_get(uri):
        # TODO: BUG: Distributed Computing Fallacy #1: The network is reliable.
        response = requests_session.get(uri, allow_redirects=False)

        if response.status_code != 200:
            raise RuntimeError(
                'Unexpected response HTTP status {} while fetching {}'.format(
                    response.status_code,
                    uri))

        return response.text
    
    return http_get


def search(search_results_uri_without_id, search_id=None, requests_session=None):
    '''
    Repeats a Texas Legislature Bill Search and returns a tuple of 
    (search_id, search_results).

        search_results_uri_without_id - the absolute URI of your BillSearchResults.aspx 
            page WITHOUT THE "ID=abc123DEF" QUERY PARAMETER!  E.g., 
            "https://capitol.texas.gov/Search/BillSearchResults.aspx?NSP=1&SPL=False&...&TT="

        search_id (OPTIONAL) - the ID of a previous search you conducted recently 
            (past day-ish?) if available.  If you omit this parameter, a new one 
            will be fetched automatically.

        requests_session (OPTIONAL) - a Requests library Session object, if you
            are using one.  If you omit this parameter, a new Session will be
            created automatically.
    '''
    session = requests_session if requests_session else requests.Session()
    http_get = _http_get_factory(session)

    id = search_id if search_id else _new_search_id(session)

    # TODO: strip out and replace the ID query parameter if it was included
    results_uri = search_results_uri_without_id + '&ID=' + id
    first_page = Page(http_get(results_uri), results_uri)
    page_seq = PageSequence(http_get, first_page)
    search_results = SearchResults(page_seq)
    return id, search_results


if __name__ == '__main__':
    # NOTICE: We chopped off the 'ID=cMVddWbvD' query param!
    SESSION_86_BILLS = 'https://capitol.texas.gov/Search/BillSearchResults.aspx?NSP=1&SPL=False&SPC=False&SPA=True&SPS=False&Leg=86&Sess=R&ChamberH=True&ChamberS=True&BillType=B;JR;CR;R;;;&AuthorCode=&SponsorCode=&ASAndOr=O&IsPA=True&IsJA=False&IsCA=False&IsPS=True&IsJS=False&IsCS=False&CmteCode=&CmteStatus=&OnDate=&FromDate=&ToDate=&FromTime=&ToTime=&LastAction=False&Actions=S000;S001;H001;&AAO=O&Subjects=&SAO=&TT=' # NO ID!

    id, search_results = search(SESSION_86_BILLS)

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


## TODO: encapsulate most of this module into a stateful class
