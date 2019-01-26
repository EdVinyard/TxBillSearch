import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import threading

from .page import Page, PageSequence, SearchResults

# TODO: Use logging module instead.
DEBUG = False

if DEBUG:
    from pprint import pprint

_BILL_SEARCH_URI = "https://capitol.texas.gov/Search/BillSearch.aspx"


def _semicolon_delimited_option_values(select_element):
    if select_element is None:
        return ''

    return ';'.join( 
        o.attrs['value']
        for o 
        in select_element.find_all('option') 
        )


def _postback_data(cold_response_text):
    ## Prepare the POSTBACK to BillSearch.aspx.
    soup = BeautifulSoup(cold_response_text, 'html.parser')
    post_data = {}

    form = soup.find(name='form', attrs={'name':'Form1'})

    for inpt in form.find_all('input'):
        try:
            name = inpt.attrs['name']
        except KeyError:
            if DEBUG: print('DEBUG: skipping unnamed form field: ' + str(inpt))
            continue

        if 'value' in inpt.attrs:
            value = inpt.attrs['value']
        elif inpt.attrs.get('checked', None) == 'checked':
            value = 'on'
        else:
            if DEBUG: print("DEBUG: skipping form field missing both 'value' and 'checked' attributes: " + str(inpt))
            continue

        post_data[name] = value

    for select in form.find_all('select'):
        name = select.attrs['name']
        
        first_option = select.find(name='option')
        selected_option = select.find(name='option', attrs={'selected':'selected'})
        if selected_option is not None:
            value = selected_option.attrs['value']
        elif first_option is not None:
            value = first_option.attrs['value']
        else:
            continue

        post_data[name] = value

    # bill subject "multi-select" special case
    subject_select = form.find(name='select', attrs={'name':'usrSubjectsFolder$lstSubjects'})
    post_data['usrSubjectsFolder$txtCodes'] = _semicolon_delimited_option_values(subject_select)

    # bill action "multi-select" special case
    actions_select = form.find(name='select', attrs={'name':'usrActionsFolder$lstActions'})
    post_data['usrActionsFolder$txtCodes'] = _semicolon_delimited_option_values(actions_select)
    
    if DEBUG: pprint(post_data)
    
    return post_data


def _new_search(session, query_without_id):
    search_uri = '{}?{}'.format(_BILL_SEARCH_URI, query_without_id)
    print(search_uri)
    
    cold_response = session.get(search_uri)
    postback_response = session.post(
        search_uri,
        data=_postback_data(cold_response.text), 
        allow_redirects=False) # <== This parameter is critical!
    relative_results_uri = postback_response.headers.get('Location', None)
    print(relative_results_uri)
    absolute_results_uri = urljoin(_BILL_SEARCH_URI, relative_results_uri)
    return absolute_results_uri


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


def _query_without_id(uri):
    '''
    The Search page requires that every query parameter be included; if any are
    omitted -- even the ones with no value -- you start with fresh search criteria
    or get an error.  So we can't use the urllib.parse.parse_qs method to 
    disassemble the query, and have to settle for string manipulation.
    '''
    uri_parts = urlparse(uri)
    return '&'.join( param 
        for param 
        in uri_parts.query.split('&') 
        if not param.startswith('ID=') )


def search(search_results_uri, requests_session=None):
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
    query_without_id = _query_without_id(search_results_uri)
    print(query_without_id)
    results_uri = _new_search(session, query_without_id)
    
    first_page = Page(http_get(results_uri), results_uri)
    page_seq = PageSequence(http_get, first_page)
    search_results = SearchResults(page_seq)
    return id, search_results


if __name__ == '__main__':
    capriglione_finance = 'https://capitol.texas.gov/Search/BillSearch.aspx?NSP=3&SPL=True&SPC=False&SPA=True&SPS=True&Leg=86&Sess=R&ChamberH=True&ChamberS=True&BillType=B;JR;CR;R;;;&AuthorCode=A2345&SponsorCode=&ASAndOr=O&IsPA=True&IsJA=False&IsCA=False&IsPS=True&IsJS=False&IsCS=False&CmteCode=&CmteStatus=&OnDate=&FromDate=&ToDate=&FromTime=&ToTime=&LastAction=False&Actions=H001;S001;&AAO=O&Subjects=I0747;I0748;&SAO=O&TT=&ID=cMVddWbvD'
    author_canales = 'https://capitol.texas.gov/Search/BillSearchResults.aspx?NSP=1&SPL=True&SPC=False&SPA=False&SPS=False&Leg=86&Sess=R&ChamberH=True&ChamberS=True&BillType=B;JR;;;;;&AuthorCode=A2340&SponsorCode=&ASAndOr=O&IsPA=True&IsJA=False&IsCA=False&IsPS=True&IsJS=False&IsCS=False&CmteCode=&CmteStatus=&OnDate=&FromDate=&ToDate=&FromTime=&ToTime=&LastAction=False&Actions=&AAO=&Subjects=&SAO=&TT=&ID=rRVjTy3oj'
    id, search_results = search(capriglione_finance)

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
