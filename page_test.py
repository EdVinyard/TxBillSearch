from page import _parse, _nearest_ancestor_table, Page, Result, PageSequence
import unittest


FULL_RESULT_PAGE_FILENAME = 'Test/BillSearchResults.aspx.FullPage.html'
with open(FULL_RESULT_PAGE_FILENAME, 'r') as f:
    FULL_RESULT_PAGE_HTML = f.read()

RESULT_LAST_PAGE_FILENAME = 'Test/BillSearchResults.aspx.LastPage.html'
with open(RESULT_LAST_PAGE_FILENAME, 'r') as f:
    RESULT_LAST_PAGE_HTML = f.read()

NO_RESULTS_PAGE_FILENAME = 'Test/BillSearchResults.aspx.NoMatches.html'
with open(NO_RESULTS_PAGE_FILENAME, 'r') as f:
    NO_RESULTS_PAGE_HTML = f.read()


class TestNearestAncestorTable(unittest.TestCase):
    markup = '''
        <html>
            <body>
                <table id="outer">
                    <tr>
                        <td id="outer_td">
                            <table id="inner">
                                <tr>
                                    <td id="inner_td"></td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
            </body>
        <html>
        '''

    @classmethod
    def setUpClass(cls):
        cls.soup = _parse(cls.markup)

    def test_element_supplied_is_table(self):
        # Arrange
        soup = TestNearestAncestorTable.soup
        inner_table = soup.find(id='inner')

        # Act
        actual = _nearest_ancestor_table(inner_table)

        # Assert
        self.assertIs(actual, soup.find(id='outer'))


    def test_normal_case(self):
        # Arrange
        soup = TestNearestAncestorTable.soup
        outer_td = soup.find(id='outer_td')

        # Act
        actual = _nearest_ancestor_table(outer_td)

        # Assert
        self.assertIs(actual, soup.find(id='outer'))        

        
    def test_no_ancestor_is_table(self):
        # Arrange
        soup = TestNearestAncestorTable.soup
        body = soup.find(name='body')

        # Act & Assert
        with self.assertRaises(ValueError):
            _nearest_ancestor_table(body)


class TestResult(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        TestResult.soup = _parse(FULL_RESULT_PAGE_HTML)
        first_txicon = TestResult.soup.find(name='img', attrs={'src':'../Images/txicon.gif'})
        assert first_txicon is not None
        TestResult.result_table = _nearest_ancestor_table(first_txicon)

    def test_title(self):
        actual = Result(TestResult.result_table)
        self.assertEqual(actual.title, 'HB 21')


class TestPage(unittest.TestCase):

    def test_total_result_count(self):
        # Act
        actual = Page(FULL_RESULT_PAGE_HTML)

        # Assert
        self.assertEqual(actual.total_result_count, 1140)

    def test_next_page_uri(self):
        # Arrange
        expected = 'BillSearchResults.aspx?CP=2&shCmte=False&shComp=False&shSumm=False&NSP=1&SPL=False&SPC=False&SPA=True&SPS=False&Leg=86&Sess=R&ChamberH=True&ChamberS=True&BillType=B;JR;;;;;&AuthorCode=&SponsorCode=&ASAndOr=O&IsPA=True&IsJA=False&IsCA=False&IsPS=True&IsJS=False&IsCS=False&CmteCode=&CmteStatus=&OnDate=&FromDate=&ToDate=&FromTime=&ToTime=&LastAction=False&Actions=S000;S001;H001;&AAO=O&Subjects=&SAO=&TT=&ID=jNkeLN5Sp'

        # Act
        actual = Page(FULL_RESULT_PAGE_HTML)

        # Assert
        self.assertEqual(actual.next_page_uri, expected)

    def test_next_page_uri_last_page(self):
        # Act 
        last_page = Page(RESULT_LAST_PAGE_HTML)
        actual = last_page.next_page_uri

        # Assert
        self.assertIsNone(actual)

    def test_results(self):
        # Act
        actual = Page(FULL_RESULT_PAGE_HTML)

        # Assert
        self.assertEqual(len(actual.results), 25)
        self.assertEqual(actual.results[0].title, 'HB 21')
        self.assertEqual(actual.results[-1].title, 'HB 45')

    def test_no_results(self):
        # Act 
        actual = Page(NO_RESULTS_PAGE_HTML)

        # Assert
        self.assertEqual(actual.total_result_count, 0)
        self.assertIsNone(actual.next_page_uri)
        self.assertEqual(actual.results, [])


class TestPagedResults(unittest.TestCase):
    def test_multiple_pages(self):
        # Arrange
        first_page_html = FULL_RESULT_PAGE_HTML
        last_page_html = RESULT_LAST_PAGE_HTML

        first_page = Page(first_page_html)
        last_page = Page(last_page_html)
        fake_http_get_call_count = 0

        def fake_http_get(uri):
            nonlocal fake_http_get_call_count
            fake_http_get_call_count += 1
            return last_page_html

        # Act
        page_seq = PageSequence(fake_http_get, first_page)
        pages = list( p for p in page_seq.pages )

        # Assert
        self.assertEqual(pages, [ first_page, last_page ])
        self.assertEqual(fake_http_get_call_count, 1)

    def test_single_page(self):
        # Arrange
        only_page_html = RESULT_LAST_PAGE_HTML
        only_page = Page(only_page_html)

        def fake_http_get(uri):
            raise RuntimeError('This should never be called!')

        # Act
        page_seq = PageSequence(fake_http_get, only_page)
        actual = list( p for p in page_seq.pages )

        # Assert
        self.assertEqual(actual, [ only_page, ])

    def test_does_NOT_load_same_page_twice(self):
        # Arrange
        first_page_html = FULL_RESULT_PAGE_HTML
        last_page_html = RESULT_LAST_PAGE_HTML

        first_page = Page(first_page_html)
        last_page = Page(last_page_html)
        fake_http_get_call_count = 0

        def fake_http_get(uri):
            nonlocal fake_http_get_call_count
            fake_http_get_call_count += 1
            return last_page_html

        # Act
        page_seq = PageSequence(fake_http_get, first_page)

        # iterate through the pages twice (but we should only 
        # see one load operation, and the resulting pages should 
        # be the same instances)
        pages1 = list( p for p in page_seq.pages )
        pages2 = list( p for p in page_seq.pages )

        # Assert
        self.assertEqual(pages1, [ first_page, last_page ])
        self.assertEqual(pages2, pages1)
        self.assertIs(pages1[0], pages2[0])
        self.assertIs(pages1[1], pages2[1])
        self.assertEqual(fake_http_get_call_count, 1)


if __name__ == '__main__':
    unittest.main()
