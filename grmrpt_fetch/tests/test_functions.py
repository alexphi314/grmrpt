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

        self.exp_groomed_runs2 = ['Game Trail', 'Lost Boy', 'Lost Boy Catwalk', '10% Road',
                                  'Dealer\'s Choice', 'Poker Flats', 'The Woods', '12 to 1 Connector',
                                  'Gopher Hill - Chair 12', 'Mil Creek Road', 'Windisch Way', 'Riva Catwalk',
                                  'Ruder\'s - Lower', 'Ruder\'s - Upper', 'Whippersnapper', 'Born Free - Lower',
                                  'Chair 15', 'Coyote Crossing', 'Cub\'s Way - Lower', 'Cub\'s Way - Upper',
                                  'Ha Ha - East', 'Lionshead Catwalk - Lower', 'Lionshead Catwalk - Upper', 'Pika',
                                  'Post Road', 'Practice Parkway', 'Spring Catwalk', 'Vail Village Catwalk - Lower',
                                  'Vail Village Catwalk - Middle', 'Vail Village Catwalk - Upper',
                                  'Born Free - Middle', 'Bwana Junction', 'Bwana Loop', 'Cascade Way',
                                  'Cheetah', 'Columbine - Lower', 'Columbine - Upper', 'Ledges - Middle',
                                  'Lodgepole - Lower', 'Lodgepole - Upper', 'Lodgepole Gulch',
                                  'Pickeroon - Lower', 'Pickeroon - Upper', 'Simba - Lower',
                                  'Simba - Middle', 'Simba - Upper', 'Cold Feet', 'Eagle\'s Nest Ridge',
                                  'Gitalong Road - Lower', 'Gitalong Road - Middle', 'Gitalong Road - Upper',
                                  'Lionsway - Lower', 'Lionsway - Upper', 'Meadows - Lower', 'Meadows - Upper',
                                  'Northface Catwalk', 'Overeasy', 'Skid Road', 'Swingsville',
                                  'Swingsville Ridge', 'Trans Montane', 'Avanti - Lower',
                                  'Avanti - Upper', 'Beartree - Lower', 'Beartree - Middle',
                                  'Beartree - Upper', 'Chaos Canyon', 'Hunky Dory',
                                  'Mid Vail Express', 'Ramshorn - Lower', 'Ramshorn - Upper',
                                  'Riva Ridge - Lower', 'Slifer Express', 'Timberline Face - East',
                                  'Timberline Face - South', 'Avanti - Middle', 'Boomer', 'Flapjack - Lower',
                                  'Flapjack - Upper', 'Sourdough', 'Sourdough - Lower', 'Timberline Catwalk',
                                  'Tin Pants', 'Tin Pants Connector', 'Choker Cutoff', 'Northwoods', 'Snag Park',
                                  'Whiskey Jack', 'Northstar', 'Game Trail', 'Lost Boy', 'Lost Boy Catwalk',
                                  '10% Road', 'Dealer\'s Choice', 'Poker Flats', 'The Woods', '12 to 1 Connector',
                                  'Gopher Hill - Chair 12', 'Mil Creek Road', 'Windisch Way', 'Riva Catwalk',
                                  'Ruder\'s - Lower', 'Ruder\'s - Upper', 'Whippersnapper', 'Born Free - Lower',
                                  'Chair 15', 'Coyote Crossing', 'Cub\'s Way - Lower', 'Cub\'s Way - Upper',
                                  'Ha Ha - East', 'Lionshead Catwalk - Lower', 'Lionshead Catwalk - Upper',
                                  'Pika', 'Post Road', 'Practice Parkway', 'Spring Catwalk',
                                  'Vail Village Catwalk - Lower', 'Vail Village Catwalk - Middle',
                                  'Vail Village Catwalk - Upper', 'Born Free - Middle', 'Bwana Junction',
                                  'Bwana Loop', 'Cascade Way', 'Cheetah', 'Columbine - Lower', 'Columbine - Upper',
                                  'Ledges - Middle', 'Lodgepole - Lower', 'Lodgepole - Upper', 'Lodgepole Gulch',
                                  'Pickeroon - Lower', 'Pickeroon - Upper', 'Simba - Lower', 'Simba - Middle',
                                  'Simba - Upper', 'Cold Feet', 'Eagle\'s Nest Ridge', 'Gitalong Road - Lower',
                                  'Gitalong Road - Middle', 'Gitalong Road - Upper', 'Lionsway - Lower',
                                  'Lionsway - Upper', 'Meadows - Lower', 'Meadows - Upper', 'Northface Catwalk',
                                  'Overeasy', 'Skid Road', 'Swingsville', 'Swingsville Ridge', 'Trans Montane',
                                  'Avanti - Lower', 'Avanti - Upper', 'Beartree - Lower', 'Beartree - Middle',
                                  'Beartree - Upper', 'Chaos Canyon', 'Hunky Dory', 'Mid Vail Express',
                                  'Ramshorn - Lower', 'Ramshorn - Upper', 'Riva Ridge - Lower', 'Slifer Express',
                                  'Timberline Face - East', 'Timberline Face - South', 'Avanti - Middle', 'Boomer',
                                  'Flapjack - Lower', 'Flapjack - Upper', 'Sourdough', 'Sourdough - Lower',
                                  'Timberline Catwalk', 'Tin Pants', 'Tin Pants Connector', 'Choker Cutoff',
                                  'Northwoods', 'Snag Park', 'Whiskey Jack', 'Northstar', 'Big Rock Park - East',
                                  'Big Rock Park - West', 'China Spur', 'Cloud 9 - Lower', 'Cloud 9 - Middle',
                                  'Cloud 9 - Upper', 'Grand Review', 'Kelly\'s Toll Road', 'The Star',
                                  'Poppy Fields East',
                                  'Poppy Fields West', 'Genghis Kahn', 'Sun Down Catwalk', 'Windows Road',
                                  'Sun Up Catwalk', 'The Slot', 'Emperor\'s Choice - Upper', 'Sleepytime Road',
                                  'Emperor\'s Choice - Lower']
        self.report_url2 = 'test_files/vail_jan2.pdf'

    def test_get_grooming_report(self) -> None:
        """
        Test function properly strips the run names from the file
        """
        date, groomed_runs = get_grooming_report(self.report_url)
        self.assertEqual(date, dt.datetime.strptime('12-23-2019', '%m-%d-%Y').date())
        self.assertListEqual(groomed_runs, self.exp_groomed_runs)

        date, groomed_runs = get_grooming_report(self.report_url2)
        self.assertEqual(date, dt.datetime(2020, 1, 2).date())
        self.assertListEqual(groomed_runs, self.exp_groomed_runs2)
