import logging
import threading
from urllib.parse import urlparse, urljoin
from pprint import pformat

import requests

from .page import Page, PageSequence, SearchResults, _parse
log = logging.getLogger(__name__)

_BILL_SEARCH_URI = "https://capitol.texas.gov/Search/BillSearch.aspx"


def _semicolon_delimited_option_values(select_element):
    '''
    Given a BeautifulSoup <select> element, return a string that contains 
    all the semicolon-delimited values of nested <option> elements.

    Example:  Returns "red;green;blue" given

        <select>
            <option value="red"></option
            <option value="green"></option
            <option value="blue"></option
        </select>
    '''
    if select_element is None:
        return ''

    return ';'.join( 
        o.attrs['value']
        for o 
        in select_element.find_all('option') 
        )


def _postback_data(cold_response_text):
    '''
    Given the raw HTML body of a ASP.NET WebForms page, returns the form
    fields for a POSTBACK.  This is NOT a generic method, as it replicates
    some Javascript fiddling with <select> elements that offer a kind of
    "multi-select" capability using a second hidden (via CSS) form field.
    '''
    ## Prepare the POSTBACK to BillSearch.aspx.
    soup = _parse(cold_response_text)
    post_data = {}

    form = soup.find(name='form', attrs={'name':'Form1'})

    for inpt in form.find_all('input'):
        try:
            name = inpt.attrs['name']
        except KeyError:
            log.debug('skipping unnamed %s', inpt)
            continue

        if 'value' in inpt.attrs:
            value = inpt.attrs['value']
        elif inpt.attrs.get('type', None) == 'checkbox':
            if inpt.attrs.get('checked', None) == 'checked':
                value = 'on'
            else:
                # unchecked checkbox
                continue
        else:
            log.debug("skipping value-less %s", inpt)
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
    
    log.debug("POSTBACK data: %s", pformat(post_data))
    return post_data


def _new_search(session, query_without_id):
    '''
    Returns a BillSearchResults.aspx URI that contains the supplied search
    criteria and a shiny, new ID.
    '''
    # The search criteria will be shuffled into form fields in the initial
    # response.
    search_uri = '{}?{}'.format(_BILL_SEARCH_URI, query_without_id)
    
    cold_response = session.get(search_uri)

    # The search criteria will be shuffled *back* into query parameters,
    # accompanied an associated ID in the POSTBACK response.
    log.debug("POST %s", _BILL_SEARCH_URI)
    postback_response = session.post(
        search_uri,
        data=_postback_data(cold_response.text), 
        allow_redirects=False) # <== This parameter is critical!
    relative_results_uri = postback_response.headers.get('Location', None)
    log.debug("Redirected to %s", relative_results_uri)
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
    omitted -- even the ones with no value -- you start with fresh search
    criteria or get an error. For that reason, we can't use the
    urllib.parse.parse_qs method to disassemble the query, but have to settle
    for string manipulation.
    '''
    uri_parts = urlparse(uri)
    return '&'.join( param 
        for param 
        in uri_parts.query.split('&') 
        if not param.startswith('ID=') )


def search(search_results_uri, requests_session=None):
    '''
    DEPRECATED: prefer txbillsearch.Search class
    '''
    ## TODO: Remove this method completely.
    s = Search(search_results_uri, requests_session)
    ## KLUDGE: return a bogus ID to avoid breaking earlier releases
    return 'FAKEID123', s.results


class Search(object):
    '''
    repeat a Texas Legislature Bill Search
    '''

    def __init__(self, search_results_uri, requests_session=None):
        '''
        search_results_uri - the absolute URI of your BillSearchResults.aspx 
            page, including all query parameters.  For example, 
            "https://capitol.texas.gov/Search/BillSearchResults.aspx?NSP=1&SPL=False&...&TT="

        requests_session (OPTIONAL) - a Requests library Session object, if you
            are using one.  If you omit this parameter, a new Session will be
            created automatically.
        '''
        self.search_results_uri = search_results_uri
        self.session = requests_session if requests_session else requests.Session()

        http_get = _http_get_factory(self.session)
        query_without_id = _query_without_id(search_results_uri)
        log.debug("Query without ID: %s", query_without_id)
        self.results_uri = _new_search(self.session, query_without_id)
        
        self.first_page = Page(http_get(self.results_uri), self.results_uri)
        self.page_seq = PageSequence(http_get, self.first_page)
        self.search_results = SearchResults(self.page_seq)

    @property
    def results(self):
        '''
        Returns a txbillsearch.page.Result generator that allows iteration
        through all the search results.  Makes HTTP requests as necessary
        to retrieve subsequent pages of search results.
        '''
        return self.search_results.bills

    @property
    def result_count(self):
        '''
        The number of bills matching the search criteria supplied to
        the constructor.
        '''
        return self.search_results.count
