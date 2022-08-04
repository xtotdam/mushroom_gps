from kivy.lang import Builder
from kivy.app import App
from kivy.properties import DictProperty, ListProperty
from kivy.clock import mainthread, Clock
from kivy.utils import platform
from kivy.logger import Logger

if platform == 'android':
    from android.storage import primary_external_storage_path
    from android.permissions import request_permissions, Permission

    primary_external_storage = primary_external_storage_path()
else:
    primary_external_storage = '.'

from plyer import notification

import json
from pathlib import Path
from datetime import datetime

if platform == 'android':
    from jnius import autoclass, cast

    from android import mActivity

    # PythonActivity = autoclass('org.kivy.android.PythonActivity')
    # Intent = autoclass('android.content.Intent')
    Context = autoclass('android.content.Context')

    LocationManager = autoclass('android.location.LocationManager')
    # Location = autoclass('android.location.Location')

    context = cast('android.content.Context', mActivity.getApplicationContext())
    locationManager = cast('android.location.LocationManager', context.getSystemService(Context.LOCATION_SERVICE))
else:
    class LocationManager:
        FUSED_PROVIDER = 'fused'
        GPS_PROVIDER = 'gps'
        NETWORK_PROVIDER = 'network'
        PASSIVE_PROVIDER = 'passive'


categories = dict(
    mushroom = 'mushroom',
    berry = 'berry',
    orientir = 'orientir',
    other = 'other'
)

osmand_markers = dict(
    mushroom = 'power_tower',
    berry = 'sport_soccer',
    orientir = 'special_flag_stroke',
    other = 'special_marker'
)


mgps_storage = Path(primary_external_storage) / 'MushroomGPS'
mgps_storage.mkdir(exist_ok=True)
json_file = mgps_storage / 'MushroomGPS.json'

def rgba(h):
    '''Takes a hex rgb string (e.g. #ffffff) and returns an RGB tuple (float, float, float).'''
    t = tuple(int(h[i:i + 2], 16) / 255. for i in (1, 3, 5)) # skip '#'
    return (t[0], t[1], t[2], 1)


# def hexrgb(l):
#     return '#{:02x}{:02x}{:02x}'.format(l[0] * 255, l[1] * 255, l[2] * 255)



class MushroomApp(App):
    loc_points = ListProperty()
    loc_dict = None
    loc_dict_fused = None
    loc_dict_gps = None

    def request_android_permissions(self):
        def callback(permissions, results):
            if all([res for res in results]):
                self.log("All permissions granted.")
            else:
                self.log("Some permissions refused.")

        request_permissions([Permission.ACCESS_COARSE_LOCATION,
                             Permission.ACCESS_FINE_LOCATION,
                             Permission.ACCESS_BACKGROUND_LOCATION,
                             Permission.WRITE_EXTERNAL_STORAGE,
                             Permission.READ_EXTERNAL_STORAGE], callback)

    def log(self, *args, **kwargs):
        Logger.info('>>>' + ' '.join(str(x) for x in args) + ' '.join('{}={}'.format(k,v) for (k,v) in kwargs.items()))


    @staticmethod
    def get_location_info(provider) -> dict:
        if platform == 'android':
            # location = locationManager.getLastKnownLocation(LocationManager.FUSED_PROVIDER)
            location = locationManager.getLastKnownLocation(provider)
            # self.log('@>>', location.toString())

            loc_dict = dict()
            loc_dict['prov'] = location.getProvider()
            loc_dict['lat'] = location.getLatitude()
            loc_dict['lon'] = location.getLongitude()
            loc_dict['alt'] = location.getAltitude()
            loc_dict['acc'] = location.getAccuracy()
            loc_dict['time'] = location.getTime() / 1000
            loc_dict['date'] = datetime.utcfromtimestamp(loc_dict['time']).strftime('%Y-%m-%d %H:%M:%S')
            loc_dict['sdate'] = datetime.utcfromtimestamp(loc_dict['time']).strftime('%M:%S')

            loc_dict['realtime'] = datetime.timestamp(datetime.now())
            loc_dict['realdate'] = datetime.utcfromtimestamp(loc_dict['realtime']).strftime('%Y-%m-%d %H:%M:%S')
            loc_dict['srealdate'] = datetime.utcfromtimestamp(loc_dict['realtime']).strftime('%M:%S')

            loc_dict['dt'] = loc_dict['realtime'] - loc_dict['time']

            return loc_dict
        else:
            fakedate = datetime.utcfromtimestamp(0).strftime('%Y-%m-%d %H:%M:%S')
            sfakedate = datetime.utcfromtimestamp(0).strftime('%M:%S')
            return dict(
                prov='fake', lat=0, lon=0, alt=0, acc=0, dt=0,
                sdate=sfakedate, srealdate=sfakedate,
                time=0, date=fakedate, realtime=0, realdate=fakedate)


    @staticmethod
    def get_location_string(loc_dict, device=True) -> str:
        NS = 'N' if loc_dict['lat'] >= 0 else 'S'
        EW = 'E' if loc_dict['lon'] >= 0 else 'W'
        s = ('{lat:.1f}{NS} {lon:.1f}{EW} ± {acc:.1f}м [{alt:.1f}м ^] <{prov:.1s}>').format(NS=NS, EW=EW, **loc_dict)
        return s


    @staticmethod
    def get_timeoffix_string(loc_dict, device=True) -> str:
        device_part = '\n{srealdate} <на устройстве>' if device else ''

        s = ('{sdate} <{prov}> [{dt:+.1f}s] {{±{acc:.1f}m}}' + device_part).format(**loc_dict)
        return s


    @mainthread
    def update_coordinates_label(self, dt):
        self.loc_dict_fused = self.get_location_info(LocationManager.FUSED_PROVIDER)
        self.loc_dict_gps = self.get_location_info(LocationManager.GPS_PROVIDER)
        # self.loc_dict_network = self.get_location_info(LocationManager.NETWORK_PROVIDER)
        # self.loc_dict_passive = self.get_location_info(LocationManager.PASSIVE_PROVIDER)

        if self.root.ids.tg_fused.state == "down":
            self.loc_dict = self.loc_dict_fused
        else:
            self.loc_dict = self.loc_dict_gps

        self.root.ids.label_coords.text = '\n'.join((
            self.get_location_string(self.loc_dict),
            self.get_timeoffix_string(self.loc_dict_fused, False),
            # self.get_timeoffix_string(self.loc_dict_network, False),
            # self.get_timeoffix_string(self.loc_dict_passive, False),
            self.get_timeoffix_string(self.loc_dict_gps)
        ))

        self.root.ids.label_dt.text = '{:+.1f}'.format(self.loc_dict["dt"])

        self.root.ids.label_log.text = '\n'.join(
            '{realdate} {title} [{category}]'.format(**x) for x in reversed(self.loc_points)
        )




    @mainthread
    def save_point(self, title, color, cat):
        if isinstance(cat, tuple):
            if cat[0] == 'down': cat = categories['mushroom']
            elif cat[1] == 'down': cat = categories['berry']
            elif cat[2] == 'down': cat = categories['orientir']
            else: cat = categories['other']

        loc = self.loc_dict.copy()
        loc['title'] = title
        loc['color'] = color
        loc['category'] = cat
        # self.log('>>>>>', loc)

        self.loc_points.append(loc.copy())
        json.dump(self.loc_points, open(json_file, 'w'), indent=2, sort_keys=True)


    def remove_last(self):
        self.loc_points.pop()


    def clear_storage(self):
        self.loc_points.clear()


    def restore_storage(self):
        try:
            self.loc_points = json.load(open(json_file))
        except FileNotFoundError:
            self.log('No json file to restore')


    def save_gpx(self):
        now = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        gpx_file = mgps_storage / 'MushroomGPS_{}.gpx'.format(now)
        self.log('>>>', gpx_file)

        head = '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>\n' +\
               '<gpx version="1.1" creator="MushroomGPS" xmlns="http://www.topografix.com/GPX/1/1" xmlns:osmand="https://osmand.net" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd">\n' +\
               f'<metadata><name>MushroomGPS {now}</name><author>MushroomGPS</author></metadata>\n'
        foot = '</gpx>'

        with open(gpx_file, 'w') as f:
            f.write(head)

            for point in self.loc_points:
                wpt = '\n'.join((
                    '<wpt lat="{lat}" lon="{lon}">',
                        '<ele>{alt}</ele>',
                        '<name>{title}</name>',
                        f'<time>{datetime.fromtimestamp(point["realtime"]).isoformat()}</time>',
                        '<desc>provider={prov}, category={category}, date={realdate}</desc>',
                        '<hdop>{acc}</hdop>',
                        '<extensions>',
                            # '<markercolor>{color}</markercolor>',
                            # '<osmand:background>circle</osmand:background>',
                            '<osmand:color>{color}</osmand:color>',
                            f'<osmand:icon>{osmand_markers[point["category"]]}</osmand:icon>',
                            '<category>{category}</category>',
                        '</extensions>',
                    '</wpt>')).format(**point)
                f.write(wpt)
                f.write('\n\n')
            f.write(foot)

        notification.notify(message=f'Записан {gpx_file.name}', toast=True)


    def save_json(self):
        now = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        json_file = mgps_storage / 'MushroomGPS_{}.json'.format(now)
        self.log('>>>', json_file)
        json.dump(self.loc_points, open(json_file, 'w'), indent=2, sort_keys=True)


    def save_files(self):
        self.save_json()
        self.save_gpx()


    def build(self):
        Clock.schedule_interval(self.update_coordinates_label, 0.3)

        if platform == "android":
            # self.log("gps.py: Android detected. Requesting permissions")
            self.request_android_permissions()

            # self.log('@@', locationManager.getAllProviders().toString())


    def on_start(self):
        try:
            self.loc_points = json.load(open(json_file, 'r'))
        except FileNotFoundError:
            self.loc_points = list()

    def on_pause(self):
        return True

    def on_resume(self):
        pass



MushroomApp().run()
