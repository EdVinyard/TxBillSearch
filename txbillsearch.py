import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs

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
BILL_SEARCH_RESULT_URI = str('https://capitol.texas.gov/Search/BillSearchResults.aspx' +
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


def parse_search_results_page(page_text):
    '''
    Extract bill names (e.g., "HB 26") from HTML fragments like this:
    
        <table width="95%">
            <tr width="100%">
                <td nowrap width="15%">
                    <a href="#" id='86R-HB 26' onClick="SetBillID(this.id); return dropdownmenu(this, event, menu)" onMouseout="delayhidemenu()">
                        <img src="../Images/txicon.gif" class="noPrint" alt="Click for options"/>
                    </a> 
                    <a href=../BillLookup/History.aspx?LegSess=86R&Bill=HB26 target="_new">
                        HB 26   
                    </a>
                </td>
        ...
    
    Start by finding the constant txicon.gif image tag, then navigate to the 
    bill name.
    '''
    soup = BeautifulSoup(page_text, 'html.parser')
    for icon in soup.find_all(name='img', attrs={'src':'../Images/txicon.gif'}):
        td = icon.parent.parent
        bill_link = td.contents[3]
        yield bill_link.string.strip()


def matching_bill_names(session, incomplete_results_uri, id):
    '''
    Run a TX Legislature activity search, given:
    
        session - a Requests Session

        incomplete_results_uri - a BillSearchResults.aspx URI 
            without the 'ID' query parameter)

        id - a "fresh" (< 24 hours old) search ID value.

    Generates all bill name strings (e.g., "HB21") from the first page of 
    results.
    '''
    results_uri = incomplete_results_uri + '&ID=' + id
    results_response = session.get(results_uri)
    yield from parse_search_results_page(results_response.text)


if __name__ == '__main__':
    session = requests.Session()
    id = new_search_id(session)     # <== THE IMPORTANT PART!
    # Substitute this "fresh" ID for the one included in old searches.

    # This is just a very simple demonstration that we can actually get 
    # search results directly from BillSearchResults.aspx.
    for bill in matching_bill_names(session, BILL_SEARCH_RESULT_URI, id):
        print(bill)


## TODO: encapsulate most of this module into a stateful class
## TODO: extract all available info for each bill
## TODO: lazily iterate over the paged search results
