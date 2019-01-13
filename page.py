from bs4 import BeautifulSoup


def _parse(html):
    return BeautifulSoup(html, 'html.parser')


def _nearest_ancestor_table(element):
    '''
    Returns the nearest ancestor of `element` that is a <table> 
    (not including the supplied element itself).
    '''
    for ancestor in element.parents:
        if ancestor.name == 'table':
            return ancestor
    
    raise ValueError('Element has no <table> ancestor!')


class Page(object):
    def __init__(self, page_text):
        soup = _parse(page_text)

        ## TODO: no results / empty page

        ## TODO: total result count

        ## TODO: next page URI

        # Each result on this page begins with
        #
        # <table width="95%">
        #   <tbody>
        #     <tr width="100%">
        #       <td width="15%" nowrap="">
        #           <a href="#" id="86R-HB 21" ...>
        #               <img src="../Images/txicon.gif" ...>
        #
        self.results = [ 
            Result(_nearest_ancestor_table(txicon))
            for txicon 
            in soup.find_all(name='img', attrs={'src':'../Images/txicon.gif'})
            ]


class Result(object):
    def __init__(self, table):
        self.table = table

        bill_link = table.find('td').contents[3]
        self.title = bill_link.string.strip()

        ## TODO: title (e.g., "HB 21")
        ## TODO: history URI (e.g., "/BillLookup/History.aspx?LegSess=86R&Bill=HB21")
        ## TODO: actions URI (e.g., "/BillLookup/Actions.aspx?LegSess=86R&Bill=HB%2021")
        ## TODO: text URI (e.g., "/BillLookup/Text.aspx?LegSess=86R&Bill=HB 21")
        ## TODO: author (e.g., "Canales")
        ## TODO: last action date (e.g., "11/12/2018")
        ## TODO: last action (e.g., "H Filed")
        ## TODO: version (e.g., "Introduced")
        ## TODO: caption (e.g., "Relating to exempting textbooks... from the sales... tax.")
