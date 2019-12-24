import datetime as dt

from django.test import TestCase

from reports.fetch_report import get_grooming_report, create_report


class ReportTestCase(TestCase):
    def test_fetch_report_1223(self) -> None:
        """
        Test function properly strips the run names from the file
        """
        date, groomed_runs = get_grooming_report('reports/tests/test_files/dec23.pdf')
        self.assertEqual(date, dt.datetime.strptime('12-23-2019', '%m-%d-%Y').date())

        exp_groomed_runs = ['Cabin Fever', 'Grubstake', 'BC Expressway - Lower', 'BC Expressway - Upper',
                            'Primrose to Strawberry Park', 'Cinch - Lower', 'Dally - Lower', 'Dally - Upper',
                            'Haymeadow', 'Latigo', 'Bridle', 'Stone Creek Meadows', 'Intertwine - Lower',
                            'Intertwine - Upper', 'Middle Primrose', 'Stacker - Lower', 'Centennial - Hohum',
                            'Cinch - Upper', 'Powell', 'Jack Rabbit Alley', 'Sheephorn - Escape',
                            'Centennial - Spruce Face', 'Park 101', 'Sawbuck', 'Redtail', 'Gold Dust',
                            'Piney']
        self.assertListEqual(groomed_runs, exp_groomed_runs)