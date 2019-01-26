from .txbillsearch import _query_without_id, _postback_data
import unittest
import os.path


TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), 'Test')
SEARCH_CRITERIA_PATH = os.path.join(TEST_DATA_DIR, 'BillSearch.aspx.CapriglioneFinance.html')


class TestQueryWithoutId(unittest.TestCase):

    def test_no_id_in_query(self):
        # Arrange
        uri = 'https://capitol.texas.gov/Search/BillSearchResults.aspx?NSP=1&SPL=True&SPC=False&SPA=False&SPS=False&Leg=86&Sess=R&ChamberH=True&ChamberS=True&BillType=B;JR;CR;R;;;&AuthorCode=A2345&SponsorCode=&ASAndOr=O&IsPA=True&IsJA=False&IsCA=False&IsPS=True&IsJS=False&IsCS=False&CmteCode=&CmteStatus=&OnDate=&FromDate=&ToDate=&FromTime=&ToTime=&LastAction=False&Actions=&AAO=&Subjects=&SAO=&TT='
        
        # Act
        actual = _query_without_id(uri)

        # Assert
        from urllib.parse import urlparse, parse_qs
        self.assertNotIn('ID=', actual)
        self.assertEqual(
            actual,
            'NSP=1&SPL=True&SPC=False&SPA=False&SPS=False&Leg=86&Sess=R&ChamberH=True&ChamberS=True&BillType=B;JR;CR;R;;;&AuthorCode=A2345&SponsorCode=&ASAndOr=O&IsPA=True&IsJA=False&IsCA=False&IsPS=True&IsJS=False&IsCS=False&CmteCode=&CmteStatus=&OnDate=&FromDate=&ToDate=&FromTime=&ToTime=&LastAction=False&Actions=&AAO=&Subjects=&SAO=&TT=')

    def test_id_in_query(self):
        # Arrange
        uri = 'https://capitol.texas.gov/Search/BillSearchResults.aspx?NSP=1&SPL=True&SPC=False&SPA=False&SPS=False&Leg=86&Sess=R&ChamberH=True&ChamberS=True&BillType=B;JR;CR;R;;;&AuthorCode=A2345&SponsorCode=&ASAndOr=O&IsPA=True&IsJA=False&IsCA=False&IsPS=True&IsJS=False&IsCS=False&CmteCode=&CmteStatus=&OnDate=&FromDate=&ToDate=&FromTime=&ToTime=&LastAction=False&Actions=&AAO=&Subjects=&SAO=&TT=&ID=cMVddWbvD'

        # Act
        actual = _query_without_id(uri)

        # Assert
        self.assertNotIn('ID=', actual)
        self.assertEqual(
            actual,
            'NSP=1&SPL=True&SPC=False&SPA=False&SPS=False&Leg=86&Sess=R&ChamberH=True&ChamberS=True&BillType=B;JR;CR;R;;;&AuthorCode=A2345&SponsorCode=&ASAndOr=O&IsPA=True&IsJA=False&IsCA=False&IsPS=True&IsJS=False&IsCS=False&CmteCode=&CmteStatus=&OnDate=&FromDate=&ToDate=&FromTime=&ToTime=&LastAction=False&Actions=&AAO=&Subjects=&SAO=&TT=')


class TestPostBackData(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(SEARCH_CRITERIA_PATH, 'r') as f:
            html = f.read()

        cls.POSTBACK_DATA = _postback_data(html)

    def setUp(self):
        self.PB = TestPostBackData.POSTBACK_DATA

    def test_input_without_name(self):
        '''
        Several name-less <input> elements have value="Reset".  
        None should appear in the POST-back data.
        '''
        self.assertNotIn('Reset', 
            [v for k,v in self.PB.items()])

    def test_input_with_value(self):
        self.assertEqual(
            self.PB['btnSearch'], 
            'Search')

    def test_input_without_value(self):
        self.assertNotIn('usrActionsFolder$dtActionFromDate', self.PB)

    def test_input_checked(self):
        self.assertEqual(
            self.PB['usrLegislatorsFolder$chkPrimaryAuthor'],
            'on')

    def test_input_unchecked(self):
        self.assertNotIn('usrLegislatorsFolder$chkJointAuthor', self.PB)

    def test_select_with_selected_option(self):
        self.assertEqual(
            self.PB['usrLegislatorsFolder$cboAuthor'], 
            'A2345')

    def test_select_without_selected_option(self):
        # All drop-down list <select> elements have a selected value
        # (as far as I can tell).
        pass

    def test_subject_codes(self):
        self.assertEqual(
            self.PB['usrSubjectsFolder$txtCodes'], 
            'I0747;I0748')

    def test_action_codes(self):
        self.assertEqual(
            self.PB['usrActionsFolder$txtCodes'],
            'H001;S001')


if __name__ == '__main__':
    unittest.main()
