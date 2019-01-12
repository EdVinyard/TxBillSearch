import requests
from bs4 import BeautifulSoup
from pprint import pprint
from urllib.parse import urlparse, parse_qs

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


def bill_search_result_uri(id):
    return BILL_SEARCH_RESULT_URI + '&ID=' + id


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


## Make the initial request to BillSearch.aspx
session = requests.Session()
cold_response = session.get(BILL_SEARCH_URI)
## to dump request: https://stackoverflow.com/questions/20658572/python-requests-print-entire-http-request-raw
## to dump response: https://stackoverflow.com/questions/16923898/how-to-get-the-raw-content-of-a-response-in-requests-with-python
#print(cold_response.headers)


## Prepare and send the POSTBACK to BillSearch.aspx to obtain an ID
soup = BeautifulSoup(cold_response.text, 'html.parser')
post_data = BILL_SEARCH_POSTBACK_PARAMS.copy()
post_data[VIEWSTATE_ID] = hidden_input_value(soup, VIEWSTATE_ID)
post_data[PREVPAGE_ID] = hidden_input_value(soup, PREVPAGE_ID)
#pprint(post_data)
postback_response = session.post(
    BILL_SEARCH_URI, 
    data=post_data, 
    allow_redirects=False)
#print(session.cookies)
print('{} => {}'.format(
    postback_response.status_code,
    postback_response.headers.get('Location', '')))


## Run the actual search on BillSearchResults.aspx using the ID
id = search_id(postback_response.headers['Location'])
results_uri = bill_search_result_uri(id)
results_response = session.get(results_uri)


# Extract the bill name from HTML fragments like this:
#
# <table width="95%">
#     <tr width="100%">
#         <td nowrap width="15%">
#             <a href="#" id='86R-HB 26' onClick="SetBillID(this.id); return dropdownmenu(this, event, menu)" onMouseout="delayhidemenu()">
#                 <img src="../Images/txicon.gif" class="noPrint" alt="Click for options"/>
#             </a> 
#             <a href=../BillLookup/History.aspx?LegSess=86R&Bill=HB26 target="_new">
#                 HB 26   
#             </a>
#         </td>
# ...
#
# Start by finding the constant txicon.gif image tag, then navigate to the 
# bill name.

soup = BeautifulSoup(results_response.text, 'html.parser')
for icon in soup.find_all(name='img', attrs={'src':'../Images/txicon.gif'}):
    td = icon.parent.parent
    bill_link = td.contents[3]
    print(bill_link.string.strip())
