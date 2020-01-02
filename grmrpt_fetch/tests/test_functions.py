import datetime as dt
import unittest

from fetch_report import get_grooming_report, create_report


class ReportFuncTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.exp_groomed_runs = ['Cabin Fever', 'Grubstake', 'BC Expressway - Lower', 'BC Expressway - Upper',
                                'Primrose to Strawberry Park', 'Cinch - Lower', 'Dally - Lower', 'Dally - Upper',
                                'Haymeadow', 'Latigo', 'Bridle', 'Stone Creek Meadows', 'Intertwine - Lower',
                                'Intertwine - Upper', 'Middle Primrose', 'Stacker - Lower', 'Centennial - Hohum',
                                'Cinch - Upper', 'Powell', 'Jack Rabbit Alley', 'Sheephorn - Escape',
                                'Centennial - Spruce Face', 'Park 101', 'Sawbuck', 'Redtail', 'Gold Dust',
                                'Piney']
        self.report_url = 'test_files/dec23.pdf'

    def test_get_grooming_report(self) -> None:
        """
        Test function properly strips the run names from the file
        """
        date, groomed_runs = get_grooming_report(self.report_url)
        self.assertEqual(date, dt.datetime.strptime('12-23-2019', '%m-%d-%Y').date())
        self.assertListEqual(groomed_runs, self.exp_groomed_runs)
