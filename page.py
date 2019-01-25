from bs4 import BeautifulSoup
import re
import datetime
import threading
import urllib.parse


DEBUG = False


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
    def _parse_results(soup, absolute_uri):
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
            Result(_nearest_ancestor_table(txicon), absolute_uri)
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
        self.results = Page._parse_results(soup, absolute_uri)

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
                            <img src="../Images/txicon.gif" class="noPrint" alt="Click for options">
                        </a>
                        <a href="../BillLookup/History.aspx?LegSess=86R&amp;Bill=HB21" target="_new">
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

    '''
    A colon followed by whitespace and the author(s) name(s).

    Example:  ":\n\t Romero, Jr. | et al.\n\t"
    '''
    _AUTHOR_PATTERN = re.compile('\s*:\s*(.*)\s*') 

    @staticmethod
    def _parse_author(tds):
        m = Result._AUTHOR_PATTERN.match(tds[1].contents[1])
        return m.group(1).strip()

    @staticmethod
    def _parse_bill_link(tds, absolute_uri):
        bill_link = tds[0].contents[3]
        title = bill_link.string.strip()
        relative_history_uri = bill_link.attrs['href']
        abs_history_uri = urllib.parse.urljoin(absolute_uri, relative_history_uri)
        return title, abs_history_uri

    _LAST_ACTION_PATTERN = re.compile('\s*(\d+/\d+/\d+)(.*)\s*')

    @staticmethod
    def _parse_last_action(tds):
        action_and_date_str = ''.join(s for s in tds[4].strings)
        m = Result._LAST_ACTION_PATTERN.match(action_and_date_str)
        action = m.group(2).strip()
        date_str = m.group(1)
        date = datetime.datetime.strptime(date_str, '%m/%d/%Y').date()
        return action, date

    def __init__(self, table, absolute_uri):
        self.table = table
        tds = [ td for td in table.find_all('td') ]

        self.author = Result._parse_author(tds)
        self.caption_version = tds[6].string.strip()
        self.caption = tds[8].string.strip()
        self.title, self.history_uri = Result._parse_bill_link(tds, absolute_uri)
        self.last_action, self.last_action_date = Result._parse_last_action(tds)

        ## TODO: actions URI (e.g., "/BillLookup/Actions.aspx?LegSess=86R&Bill=HB%2021")
        ## TODO: text URI (e.g., "/BillLookup/Text.aspx?LegSess=86R&Bill=HB 21")

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.history_uri == other.history_uri
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return '{title} by {author} {last_action} {last_action_date}'.format(**self.__dict__)

    def __repr__(self):
        return self.__str__()
