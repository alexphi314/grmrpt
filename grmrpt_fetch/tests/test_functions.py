import datetime as dt
import pytz
import unittest
import os
import sys
import subprocess
import time
from collections import Counter
from copy import deepcopy

import requests

from fetch_server import get_grooming_report, kill_tika_server

if sys.version_info.major < 3:
    from urllib import url2pathname
else:
    from urllib.request import url2pathname

# https://stackoverflow.com/questions/10123929/fetch-a-file-from-a-local-url-with-python-requests
class LocalFileAdapter(requests.adapters.BaseAdapter):
    """Protocol Adapter to allow Requests to GET file:// URLs

    @todo: Properly handle non-empty hostname portions.
    """

    @staticmethod
    def _chkpath(method, path):
        """Return an HTTP status for the given filesystem path."""
        if method.lower() in ('put', 'delete'):
            return 501, "Not Implemented"  # TODO
        elif method.lower() not in ('get', 'head'):
            return 405, "Method Not Allowed"
        elif os.path.isdir(path):
            return 400, "Path Not A File"
        elif not os.path.isfile(path):
            return 404, "File Not Found"
        elif not os.access(path, os.R_OK):
            return 403, "Access Denied"
        else:
            return 200, "OK"

    def send(self, req, **kwargs):  # pylint: disable=unused-argument
        """Return the file specified by the given request

        @type req: C{PreparedRequest}
        @todo: Should I bother filling `response.headers` and processing
               If-Modified-Since and friends using `os.stat`?
        """
        path = os.path.normcase(os.path.normpath(url2pathname(req.path_url)))
        response = requests.Response()

        response.status_code, response.reason = self._chkpath(req.method, path)
        if response.status_code == 200 and req.method.lower() != 'head':
            try:
                response.raw = open(path, 'rb')
            except (OSError, IOError) as err:
                response.status_code = 500
                response.reason = str(err)

        if isinstance(req.url, bytes):
            response.url = req.url.decode('utf-8')
        else:
            response.url = req.url

        response.request = req
        response.connection = self

        return response

    def close(self):
        pass


class ReportFuncTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.maxDiff = None
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
                                  'Whiskey Jack', 'Northstar', 'Big Rock Park - East',
                                  'Big Rock Park - West', 'China Spur', 'Cloud 9 - Lower', 'Cloud 9 - Middle',
                                  'Cloud 9 - Upper', 'Grand Review', 'Kelly\'s Toll Road', 'The Star',
                                  'Poppy Fields East',
                                  'Poppy Fields West', 'Genghis Kahn', 'Sun Down Catwalk', 'Windows Road',
                                  'Sun Up Catwalk', 'The Slot', 'Emperor\'s Choice - Upper', 'Sleepytime Road',
                                  'Emperor\'s Choice - Lower']
        self.report_url2 = 'test_files/vail_jan2.pdf'

        self.exp_groomed_runs3 = [
            'Cresta',
            'Golden Bear',
            'Leav the Beav',
            'Cabin Fever',
            'Roughlock',
            'Redtail',
            'BC Expressway - Lower',
            'BC Expressway - Upper',
            'Larkspur - Lower',
            'Larkspur - Upper',
            'Primrose to Strawberry Park',
            'Lupine',
            'Shooting Star',
            'Cinch - Lower',
            'Dally - Lower',
            'Dally - Upper',
            'Haymeadow',
            'Gold Dust',
            'Latigo',
            'Intertwine - Lower',
            'Intertwine - Upper',
            'Middle Primrose',
            'Primrose',
            'President Ford\'s - Lower',
            'Stacker - Lower',
            'Cinch - Upper',
            'Solitude',
            'Sheephorn - Escape',
            'Centennial - Spruce Face',
            'Little Brave',
            'Sawbuck',
            'Centennial - Hohum',
            'Red Buffalo'
        ]
        self.report_url3 = 'test_files/bc_jan7.pdf'

        self.exp_groomed_runs4 = [
            'Arc',
            'Bashor',
            'B.C. Ski Way',
            'Beeline',
            'Between',
            'Betwixt',
            'Blizzard',
            'Boulevard',
            'Broadway',
            'Buckshot',
            'Buddy\'s Run',
            'Calf Roper',
            'Chisholm Trail',
            'Chuckwagon',
            'Concentration Lower',
            'Cyclone',
            'Daybreak',
            'Drop Out',
            'Dusk',
            'Duster',
            'Eagles Nest',
            'Ego',
            'Flatout',
            'Flintlock',
            'Flying Z',
            'Flying Z Gulch',
            'Giggle Gulch',
            'Half Hitch',
            'Headwall North',
            'Heavenly Daze',
            'Highline',
            'High Noon',
            'Huffman\'s',
            'Jess\' Cut-Off',
            'Kit',
            'Last Chance',
            'Lightning',
            'Lil\' Rodeo Park',
            'Longhorn',
            'Main Drag',
            'Maverick\'s Half Pipe',
            'Meadow Lane',
            'Moonlight',
            'NASTAR Race Area',
            'One O\'Clock',
            'Over Easy',
            'Park Lane',
            'Preview',
            'Pup',
            'Quickdraw',
            'Rabbit Ears Terrain Park',
            'Rainbow',
            'Ramrod',
            'Rendezvous Way',
            'Right-O-Way',
            'Rough Rider Basin',
            'Round About',
            'Rowel',
            'Rudi\'s Run',
            'See Me',
            'Short Cut',
            'Sitz',
            'Sitzback',
            'Skyline',
            'South Peak Flats',
            'So What',
            'Spike',
            'Spur Run',
            'Stampede',
            'Storm Peak Catwalk',
            'Storm Peak South',
            'Sundial',
            'Sunset',
            'Sunshine Lift Line',
            'Swinger',
            'Ted\'s Ridge',
            'Tomahawk',
            'Tomahawk Face',
            'Tornado Lane',
            'Tower',
            'Traverse',
            'Two O\'Clock',
            'Vagabond',
            'Valley View',
            'Valley View Lower',
            'Velvet',
            'Vogue',
            'West Side',
            'Why Not',
            'Yoo Hoo',
            'Corridor',
            'Cowboy Coffee',
            'Rooster',
            'Snooze Bar'
        ]
        self.report_url4 = 'test_files/sb_jan16.json'
        #self.report_url4 = 'https://www.steamboat.com/the-mountain/mountain-report#/'

        self.report_url5 = 'test_files/vail_feb7.pdf'

        self.report_url6 = 'test_files/breck_feb18.pdf'
        self.exp_groomed_runs6 = [
            'Claimjumper',
            'Crescendo',
            'Crosscut',
            'Dukes',
            'Dyersville',
            'Freeway Pipe',
            'Frosty\'s',
            'Lower 4 O\'Clock',
            'Middle 4 O\'Clock',
            'Northstar',
            'Park Lane Park',
            'Power Line',
            'Springmeier',
            'Spruce',
            'Swinger',
            'Trygves',
            'Twister',
            'American',
            'Bonanza',
            'Briar Rose',
            'Cashier',
            'Columbia',
            'Country Boy',
            'Eldorado',
            'Frontier',
            'Gold King',
            'Little Burn',
            'Lower American',
            'Lower Lehman',
            'Middle Lehman',
            'Peerless',
            'Red Rover',
            'Sawmill',
            'Shock',
            'Silverthorne',
            'Snowflake',
            'Sundown',
            'Upper Lehman',
            'Volunteer',
            'Centennial',
            'Cimarron',
            'Crystal',
            'Double Jack',
            'Flap Jack',
            'Angels Rest',
            'Fort Mary B',
            'Lincoln Mdws',
            'Lower Forget',
            'Monte Cristo',
            'Pioneer',
            'Swan City',
            'Wirepatch',
            'Upper 4 O\'Clock',
            'Alpine Alley',
            'Pika'
        ]

        self.report_url7 = 'test_files/breck_feb19.pdf'
        self.exp_groomed_runs7 = deepcopy(self.exp_groomed_runs6)
        self.exp_groomed_runs7.remove('Swan City')

        self.report_url8 = 'test_files/bc_mar3.json'
        self.exp_groomed_runs8 = [
            'Booth Gardens',
            'Bridle',
            'Centennial-Upper',
            'Cinch-Lower',
            'Cinch-Upper',
            'Cookie Crumble',
            'Dally',
            'Haymeadow',
            'Piney',
            'Powell',
            'Red Buffalo',
            'Sheephorn-Upper',
            'Solitude',
            '1876',
            'Centennial-Lower',
            'EpicMix Race',
            'Gold Dust',
            'Latigo-Lower',
            'Latigo-Upper',
            'Red Tail',
            'Centennial-Spruce Face',
            'Centennial-Willy\'s Face',
            'Park 101',
            'Zoom Room',
            'Stone Creek Meadows',
            'Larkspur Bowl',
            'Larkspur-Lower',
            'Beaver Creek Mountain Expressway',
            'Primrose',
            'Bitterroot',
            'President Ford\'s-Lower',
            'Stacker-Lower',
            'President Ford\'s',
            'Intertwine',
            'Leav the Beav',
            'Sawbuck',
            'Cabin Fever',
            'Grubstake',
            'Gunders',
            'Roughlock-Lower',
            'Stirrup',
            'Golden Bear',
            'Little Brave',
            'Roughlock-Upper'
        ]
        self.report_url8_pdf = 'test_files/bc_mar3.pdf'

    def test_get_grooming_report(self) -> None:
        """
        Test function properly strips the run names from the file
        """
        date, groomed_runs = get_grooming_report('tika', self.report_url)
        self.assertEqual(date, dt.datetime.strptime('12-23-2019', '%m-%d-%Y').date())
        self.assertListEqual(groomed_runs, self.exp_groomed_runs)

        date, groomed_runs = get_grooming_report('tika', self.report_url2)
        self.assertEqual(date, dt.datetime(2020, 1, 2).date())
        self.assertListEqual(groomed_runs, self.exp_groomed_runs2)

        date, groomed_runs = get_grooming_report('tika', self.report_url3)
        self.assertEqual(date, dt.datetime(2020, 1, 7).date())
        self.assertListEqual(groomed_runs, self.exp_groomed_runs3)

        requests_session = requests.session()
        requests_session.mount('file://', LocalFileAdapter())
        response = requests_session.get('file://{}/{}'.format(os.getcwd(), self.report_url4))
        date, groomed_runs = get_grooming_report('json', response=response)
        self.assertEqual(date, dt.datetime(2020, 1, 16, tzinfo=pytz.timezone('US/Mountain')).date())
        self.assertListEqual(groomed_runs, self.exp_groomed_runs4)

        date, groomed_runs = get_grooming_report('tika', self.report_url5)
        self.assertEqual(date, dt.datetime(2020, 2, 7).date())
        self.assertEqual(len(groomed_runs), 113)
        # TODO: Fix REGEX so these tests pass
        # self.assertFalse('Whiskey Jack GAME CREEK BOWL' in groomed_runs)
        # self.assertTrue('Whiskey Jack' in groomed_runs)

        date, groomed_runs = get_grooming_report('tika', self.report_url6)
        self.assertEqual(date, dt.datetime(2020, 2, 18).date())
        self.assertEqual(Counter(groomed_runs), Counter(self.exp_groomed_runs6))

        date, groomed_runs = get_grooming_report('tika', self.report_url7)
        self.assertEqual(date, dt.datetime(2020, 2, 19).date())
        self.assertEqual(Counter(groomed_runs), Counter(self.exp_groomed_runs7))

        response = requests_session.get('file://{}/{}'.format(os.getcwd(), self.report_url8))
        date, groomed_runs = get_grooming_report('json-vail', response=response)
        self.assertEqual(date, dt.datetime(2020, 3, 3).date())
        self.assertEqual(Counter(groomed_runs), Counter(self.exp_groomed_runs8))


class TestTikaRelaunch(unittest.TestCase):
    def setUp(self) -> None:
        self.report_url = 'test_files/bc_jan7.pdf'

    def test_relaunch(self) -> None:
        # Launch tika server
        get_grooming_report('tika', self.report_url)

        # Confirm tika is launched
        with subprocess.Popen(['ps', 'aux'], stdout=subprocess.PIPE) as ps:
            with subprocess.Popen(['grep', '[t]ika'], stdin=ps.stdout, stdout=subprocess.PIPE) as grep:
                grep_out, _ = grep.communicate()
                grep_out = str(grep_out)

                ps.kill()
                grep.kill()

        self.assertEqual(len(grep_out.split('\n')), 1)

        # Kill tika server
        kill_tika_server()

        # Confirm tika is not running
        time.sleep(1)

        with subprocess.Popen(['ps', 'aux'], stdout=subprocess.PIPE) as ps:
            with subprocess.Popen(['grep', '[t]ika'], stdin=ps.stdout, stdout=subprocess.PIPE) as grep:
                grep_out2, _ = grep.communicate()
                self.assertEqual(b'', grep_out2)

                ps.kill()
                grep.kill()


if __name__ == '__main__':
    unittest.main()
