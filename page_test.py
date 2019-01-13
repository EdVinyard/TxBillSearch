from page import _parse, _nearest_ancestor_table, Page, Result
import unittest

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
        with open('Test/BillSearchResults.aspx.FullPage.html', 'r') as f:
            TestResult.html = f.read()

        TestResult.soup = _parse(TestResult.html)
        first_txicon = TestResult.soup.find(name='img', attrs={'src':'../Images/txicon.gif'})
        assert first_txicon is not None
        TestResult.result_table = _nearest_ancestor_table(first_txicon)

    def test_title(self):
        actual = Result(TestResult.result_table)
        self.assertEqual(actual.title, 'HB 21')


if __name__ == '__main__':
    unittest.main()
