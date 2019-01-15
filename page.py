from bs4 import BeautifulSoup
import re
import threading
import urllib.parse


DEBUG = True


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


class SearchResults(object):
    def __init__(self, page_sequence):
        self.page_seq = page_sequence

    @property
    def count(self):
        return self.page_seq.total_result_count

    @property
    def bills(self):
        '''
        A continuous iterator over the bills in the pages of results.
        Subsequent pages are loaded lazily, as the iterator "touches"
        them for the first time.
        '''
        for page in self.page_seq.pages:
            yield from page.results


class PageSequence(object):
    '''
    A sequence of pages of results, displayed on BillSearchResults.aspx,
    parsed into structured data.  
    
    For example, if there are 100 results, BillSearchResults.aspx displays 
    25 results on a page, so an instance of PageSequence would represent
    all four pages of results, available through the `PageSequence.pages`
    property.
    '''    
    def __init__(self, http_get, first_page):
        self._http_get = http_get

        ## lazily load subsequent pages
        self._pages = [ first_page, ]
        self._pages_lock = threading.Condition()

    # TODO: Make this class iterable and get rid of this property.
    @property
    def pages(self):
        page_index = 0
        while page_index < len(self._pages):
            yield self._pages[page_index]
            page_index += 1
        
        while not self._all_pages_loaded():
            self._ensure_page_loaded(page_index)
            yield self._pages[page_index]
            page_index += 1

    @property
    def total_result_count(self):
        return self._pages[0].total_result_count

    def _all_pages_loaded(self):
        return self._pages[-1].next_page_uri is None

    def _ensure_page_loaded(self, page_index):
        if len(self._pages) > page_index:
            return

        with self._pages_lock:
            while page_index >= len(self._pages) and not self._all_pages_loaded():
                last_loaded_page = self._pages[-1]
                uri = last_loaded_page.next_page_uri
                
                if DEBUG:
                    print('fetching {}...'.format(uri))

                # TODO: BUG: Distributed Computing Fallacy #1: The network is reliable.
                response_body = self._http_get(uri)
                self._pages.append(Page(response_body, uri))


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
    def _parse_next_page_uri(soup, absolute_uri):
        '''
        Each "Next Page" link looks like

            <a href="BillSearchResults.aspx?CP=2&...">
                <img valign="bottom" 
                     src="../Images/icon_next_active.gif" 
                     alt="Navigate to next page">
            </a>
        '''
        img = soup.find(name='img', attrs={'alt':'Navigate to next page'})
        
        if img is None:
            return None

        a = img.parent
        relative_uri = a.attrs['href'] # e.g., "BillSearchResults.aspx?CP=3&..."
        return urllib.parse.urljoin(absolute_uri, relative_uri)

    def __init__(self, page_text, absolute_uri):
        soup = _parse(page_text)

        self.absolute_uri = absolute_uri
        self.next_page_uri = Page._parse_next_page_uri(soup, absolute_uri)
        self.total_result_count = Page._parse_total_result_count(soup)
        self.results = Page._parse_results(soup)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.next_page_uri == other.next_page_uri \
                and self.total_result_count == other.total_result_count \
                and self.results == other.results
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    FORMAT = '''
        Page
            next_page_uri: {next_page_uri}
            total_result_count: {total_result_count}
            results: {results}
        '''

    def __str__(self):
        return Page.FORMAT.format(**self.__dict__)

    def __repr__(self):
        return self.__str__()


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

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            # TODO: BUG: This should compare Bill Text URIs instead of just the name.
            return self.title == other.title
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return self.title

    def __repr__(self):
        return self.__str__()
