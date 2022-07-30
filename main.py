from kivy.lang import Builder
from kivy.app import App
from kivy.properties import StringProperty, ObjectProperty, NumericProperty, DictProperty, ListProperty
from kivy.clock import mainthread, Clock
from kivy.utils import platform
from kivy.logger import Logger

if platform == 'android':
    from android.storage import primary_external_storage_path
    from android.permissions import request_permissions, Permission

    primary_external_storage = primary_external_storage_path()
else:
    primary_external_storage = '.'

from plyer import gps

import uuid
import json
import os.path
from functools import partial
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



json_file = os.path.join(primary_external_storage, 'mushroomGps.json')
# kml_file = os.path.join(primary_external_storage, 'mushroomGps.kml')
gpx_file = os.path.join(primary_external_storage, 'mushroomGps.gpx')


def rgba(h):
    '''Takes a hex rgb string (e.g. #ffffff) and returns an RGB tuple (float, float, float).'''
    t = tuple(int(h[i:i + 2], 16) / 255. for i in (1, 3, 5)) # skip '#'
    return (t[0], t[1], t[2], 1)


def hexrgb(l):
    return '#' + ''.join(hex(int(x * 255))[2:] for x in l[:3])


def get_coordinates():
    pass





class MushroomApp(App):
    loc_points = ListProperty()
    loc_dict = None

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
        Logger.info(' '.join(str(x) for x in args) + ' '.join('{}={}'.format(k,v) for (k,v) in kwargs.items()))


    @mainthread
    def update_coordinates_label(self, dt):
        if platform == 'android':
            location = locationManager.getLastKnownLocation(LocationManager.FUSED_PROVIDER)
            self.log('@>>', location.toString())

            self.loc_dict = dict()
            self.loc_dict['prov'] = location.getProvider()
            self.loc_dict['lat'] = location.getLatitude()
            self.loc_dict['lon'] = location.getLongitude()
            self.loc_dict['alt'] = location.getAltitude()
            self.loc_dict['acc'] = location.getAccuracy()
            self.loc_dict['time'] = location.getTime() // 1000
            self.loc_dict['date'] = datetime.utcfromtimestamp(self.loc_dict['time']).strftime('%Y-%m-%d %H:%M:%S')

            self.loc_dict['realtime'] = int(datetime.timestamp(datetime.now()))
            self.loc_dict['realdate'] = datetime.utcfromtimestamp(self.loc_dict['realtime']).strftime('%Y-%m-%d %H:%M:%S')

            self.root.ids.label_coords.text =\
                '{lat:.3f}  {lon:.3f}  ± {acc:.1f}м [{alt:.1f}м н.у.м.]\n{date} <{prov}>\n{realdate} <на устройстве>'.format(**self.loc_dict)

            # self.log(self.loc_dict)

            self.root.ids.label_log.text = '\n'.join(
                '{realdate} {title}'.format(**x) for x in reversed(self.loc_points)
            )

        else:
            self.root.ids.label_coords.text = uuid.uuid4().hex.upper()
            self.root.ids.label_log.text = '\n'.join(uuid.uuid4().hex.upper() for x in range(10))


    @mainthread
    def save_point(self, title, color):
        # points = json.load(open(json_file))
        loc = self.loc_dict.copy()
        loc['title'] = title
        loc['color'] = hexrgb(color)
        # self.log('>>>>>', loc)

        self.loc_points.append(loc.copy())
        json.dump(self.loc_points, open(json_file, 'w'), indent=2, sort_keys=True)



    def save_kml(self):
        pass



    def save_gpx(self):
        now = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        gpx_file = os.path.join(primary_external_storage, 'mushroomGps_{}.gpx'.format(now))
        self.log('>>>', gpx_file)

        waypoints = list()
        for point in self.loc_points:
            wpt = (
                '<wpt lat="{lat}" lon="{lon}">' + \
                    '<ele>{alt}</ele>' +\
                    '<name>{title}</name>' +\
                    f'<time>{datetime.fromtimestamp(point["realtime"]).isoformat()}</time>' +\
                    '<desc>{prov}</desc>' +\
                    '<hdop>{acc}</hdop>' +\
                    '<extensions><markercolor>{color}</markercolor></extensions>' +\
                '</wpt>\n').format(**point)
            waypoints.append(wpt)
        head = '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>\n' +\
               '<gpx version="1.1" creator="MushroomGPS" xmlns="http://www.topografix.com/GPX/1/1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd">\n'
        foot = '</gpx>'

        with open(gpx_file, 'w') as f:
            f.write(head)
            for w in waypoints:
                f.write(w)
            f.write(foot)


    def build(self):
        Clock.schedule_interval(self.update_coordinates_label, 0.5)

        if platform == "android":
            self.log("gps.py: Android detected. Requesting permissions")
            self.request_android_permissions()

            self.log('@@', locationManager.getAllProviders().toString())




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
