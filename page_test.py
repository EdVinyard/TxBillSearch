from page import _parse, _nearest_ancestor_table, Page, Result
import unittest


FULL_RESULT_PAGE_FILENAME = 'Test/BillSearchResults.aspx.FullPage.html'
RESULT_LAST_PAGE_FILENAME = 'Test/BillSearchResults.aspx.LastPage.html'
NO_RESULTS_PAGE_FILENAME = 'Test/BillSearchResults.aspx.NoMatches.html'


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
        with open(FULL_RESULT_PAGE_FILENAME, 'r') as f:
            TestResult.html = f.read()

        TestResult.soup = _parse(TestResult.html)
        first_txicon = TestResult.soup.find(name='img', attrs={'src':'../Images/txicon.gif'})
        assert first_txicon is not None
        TestResult.result_table = _nearest_ancestor_table(first_txicon)

    def test_title(self):
        actual = Result(TestResult.result_table)
        self.assertEqual(actual.title, 'HB 21')


class TestPage(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(FULL_RESULT_PAGE_FILENAME, 'r') as f:
            TestPage.html = f.read()

    def test_total_result_count(self):
        # Act
        actual = Page(TestPage.html)

        # Assert
        self.assertEqual(actual.total_result_count, 1140)

    def test_next_page_uri(self):
        # Arrange
        expected = 'BillSearchResults.aspx?CP=2&shCmte=False&shComp=False&shSumm=False&NSP=1&SPL=False&SPC=False&SPA=True&SPS=False&Leg=86&Sess=R&ChamberH=True&ChamberS=True&BillType=B;JR;;;;;&AuthorCode=&SponsorCode=&ASAndOr=O&IsPA=True&IsJA=False&IsCA=False&IsPS=True&IsJS=False&IsCS=False&CmteCode=&CmteStatus=&OnDate=&FromDate=&ToDate=&FromTime=&ToTime=&LastAction=False&Actions=S000;S001;H001;&AAO=O&Subjects=&SAO=&TT=&ID=jNkeLN5Sp'

        # Act
        actual = Page(TestPage.html)

        # Assert
        self.assertEqual(actual.next_page_uri, expected)

    def test_next_page_uri_last_page(self):
        # Arrange
        with open(RESULT_LAST_PAGE_FILENAME, 'r') as f:
            html = f.read()

        # Act 
        last_page = Page(html)
        actual = last_page.next_page_uri

        # Assert
        self.assertIsNone(actual)

    def test_results(self):
        # Act
        actual = Page(TestPage.html)

        # Assert
        self.assertEqual(len(actual.results), 25)
        self.assertEqual(actual.results[0].title, 'HB 21')
        self.assertEqual(actual.results[-1].title, 'HB 45')

    def test_no_results(self):
        # Arrange
        with open(NO_RESULTS_PAGE_FILENAME, 'r') as f:
            html = f.read()

        # Act 
        actual = Page(html)

        # Assert
        self.assertEqual(actual.total_result_count, 0)
        self.assertIsNone(actual.next_page_uri)
        self.assertEqual(actual.results, [])


if __name__ == '__main__':
    unittest.main()
