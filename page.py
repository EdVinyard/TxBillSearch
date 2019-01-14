from bs4 import BeautifulSoup
import re


def _parse(html):
    '''
    Internally and in test, prefer this method to calling 
    the BeautifulSoup constructor directly, so that the
    parser can be changed out later, if desired.
    '''
    return BeautifulSoup(html, 'html.parser')


def _nearest_ancestor_table(element):
    '''
    Given a BeautifulSoup element, returns the nearest ancestor 
    <table> of that element, not including the supplied element 
    itself.
    '''
    for ancestor in element.parents:
        if ancestor.name == 'table':
            return ancestor
    
    raise ValueError('Element has no <table> ancestor!')


class Page(object):
    '''
    A single page of results, displayed on BillSearchResults.aspx,
    parsed into structured data.
    '''
    RESULT_COUNT_PATTERN = re.compile(
        "Bills [\d,]+ through [\d,]+ out of ([\d,]+) matches.", 
        re.IGNORECASE)

    @staticmethod
    def _parse_total_result_count(soup):
        '''
        Each total result count looks like
        
         <span id="lblMatches" style="display:inline-block;">
             Bills 1 through 25 out of 1,140 matches.
         </span>
        '''
        lbl_str = soup.find(id='lblMatches').string

        if lbl_str is None:
            return 0

        m = Page.RESULT_COUNT_PATTERN.search(lbl_str)
        return int(m.group(1).replace(',', ''))

    @staticmethod
    def _parse_results(soup):
        '''
        Each result on this page begins with
        
         <table width="95%">
           <tbody>
             <tr width="100%">
               <td width="15%" nowrap="">
                   <a href="#" id="86R-HB 21" ...>
                       <img src="../Images/txicon.gif" ...>
        '''
        return [ 
            Result(_nearest_ancestor_table(txicon))
            for txicon 
            in soup.find_all(name='img', attrs={'src':'../Images/txicon.gif'})
            ]

    @staticmethod
    def _parse_next_page_uri(soup):
        img = soup.find(name='img', attrs={'alt':'Navigate to next page'})
        
        if img is None:
            return None

        a = img.parent
        return a.attrs['href']

    def __init__(self, page_text):
        soup = _parse(page_text)

        self.next_page_uri = Page._parse_next_page_uri(soup)
        self.total_result_count = Page._parse_total_result_count(soup)
        self.results = Page._parse_results(soup)


class Result(object):
    '''
    An individual result, displayed on BillSearchResults.aspx,
    parsed into structured data.  An example of the markup follows.

        <table width="95%">
            <tbody>
                <tr width="100%">
                    <td width="15%" nowrap="">
                        <a href="#" id="86R-HB 21" onclick="SetBillID(this.id); return dropdownmenu(this, event, menu)"
                            onmouseout="delayhidemenu()">
                            <img src="../Images/txicon.gif" class="noPrint" alt="Click for options"></a> <a href="../BillLookup/History.aspx?LegSess=86R&amp;Bill=HB21"
                            target="_new">
                            HB 21
                        </a>
                    </td>
                    <td width="55%" valign="bottom" nowrap="" align="left"><strong>Author</strong>:
                        Canales
                    </td>
                    <td width="35%" valign="bottom" nowrap="" align="left"></td>
                </tr>
                <tr>
                    <td width="130" height="12"><strong>Last Action</strong>:&nbsp;</td>
                    <td colspan="2" height="12"><em>11/12/2018 H Filed</em></td>
                </tr>
                <tr>
                    <td width="130" nowrap=""><strong>Caption Version</strong>:</td>
                    <td colspan="2">Introduced</td>
                </tr>
                <tr>
                    <td width="130" valign="top"><strong>Caption</strong>:</td>
                    <td colspan="2">Relating to exempting textbooks purchased, used, or consumed by university and college
                        students from the sales and use tax for limited periods.</td>
                </tr>
            </tbody>
        </table>    
    '''
    def __init__(self, table):
        self.table = table

        bill_link = table.find('td').contents[3]
        self.title = bill_link.string.strip()

        ## TODO: history URI (e.g., "/BillLookup/History.aspx?LegSess=86R&Bill=HB21")
        ## TODO: actions URI (e.g., "/BillLookup/Actions.aspx?LegSess=86R&Bill=HB%2021")
        ## TODO: text URI (e.g., "/BillLookup/Text.aspx?LegSess=86R&Bill=HB 21")
        ## TODO: author (e.g., "Canales")
        ## TODO: last action date (e.g., "11/12/2018")
        ## TODO: last action (e.g., "H Filed")
        ## TODO: version (e.g., "Introduced")
        ## TODO: caption (e.g., "Relating to exempting textbooks... from the sales... tax.")
