#coding:utf8
"""
for graphics magick
"""
EXIF_KEYS = {
    'make': 'Make',
    'model': 'Model',
    'exposure': 'Exposure Time', # 曝光时间
    'datetime': 'Date Time Original',
    'datetime_mk': 'Date Time',
    'fn': 'F Number', #光圈系数
    'orientation': 'Orientation',

    'program': 'Exposure Program',
    'iso': 'ISO Speed Ratings',
    'focal_length': 'Focal Length',
    'latitude': 'GPS Latitude',
    'latitude_ref': 'GPS Latitude Ref',
    'longitude': 'GPS Longitude',
    'longitude_ref': 'GPS Longitude Ref',
    'altitude': 'GPS Altitude',
    'altitude_ref': 'GPS Altitude Ref',
    'width': 'Exif Image Width',
    'height': 'Exif Image Length',

    'speed': 'Shutter Speed Value', # 快门速度值
    'av': 'Aperture Value', # 光圈值，0-?整数，类似档数
    'flash': 'Flash',
    'metering': 'Metering Mode',
    'distance': 'SubjectDistance',
}


def convert_to_degress(value):
    """Helper function to convert the GPS coordinates stored in the EXIF to degress in float format"""
    if value is None:
        return

    d0 = value[0][0]
    d1 = value[0][1]
    d = float(d0) / float(d1)

    m0 = value[1][0]
    m1 = value[1][1]
    m = float(m0) / float(m1)

    s0 = value[2][0]
    s1 = value[2][1]
    s = float(s0) / float(s1)

    return abs(d + (m / 60.0) + (s / 3600.0))


EXIF_FUNCS ={
    'exposure': lambda x: int(x) if isinstance(x, float) else x ,
    'focal_length': int,
    'iso': int,
    'program': int,
    'orientation': int,
    'flash': int,
    'metering': int,
    'width': int,
    'height': int,
    'av': int,
    'longitude': convert_to_degress,
    'latitude': convert_to_degress,
    'altitude': convert_to_degress,
    'longitude_ref': lambda x: x.upper(),
    'latitude_ref': lambda x: x.upper(),
    'altitude_ref': int,
}


ORIENTATIONS = {
    1: ("Normal", 0),
    2: ("Mirrored left-to-right", 0),
    3: ("Rotated 180 degrees", 180),
    4: ("Mirrored top-to-bottom", 0),
    5: ("Mirrored along top-left diagonal", 0),
    6: ("Rotated 90 degrees", 90),
    7: ("Mirrored along top-right diagonal", 0),
    8: ("Rotated 270 degrees", 270)
}


class Exif(object):
    def __init__(self, im, auto_orientation=False):
        """最后通过exif.data来获取信息"""
        self.data = {}
        for key in EXIF_KEYS:
            exif_key = 'EXIF:%s' % EXIF_KEYS[key].replace(' ', '')
            value = im.attribute(exif_key)
            if value != 'unknown' and value: # 有数值的
                value = self.decode_value(value)

                value = self.for_human(value, EXIF_FUNCS.get(key))

                self.data[key] = value

        # 为经纬度做重新处理
        if 'latitude_ref' in self.data and 'latitude' in self.data:
            if self.data['latitude_ref'] != 'N':
                self.data['latitude'] = -self.data['latitude']

        if 'longitude_ref' in self.data and 'longitude' in self.data:
            if self.data['longitude_ref'] != 'E':
                self.data['longitude'] = -self.data['longitude']

        if 'altitude_ref' in self.data and 'altitude' in self.data:
            if self.data['altitude'] == 1:
                self.data['altitude'] = -self.data['altitude']

        # 转正，需要的角度
        self.degrees = 0
        orientation = self.data.get('orientation')
        if self.data.get('orientation') in [3, 6, 8]:
            self.degrees = ORIENTATIONS[orientation][1]
            if auto_orientation:  # 自动旋转图片
                im.rotate(self.degrees)

    @staticmethod
    def decode_value(value):
        def str_to_tuple(v):
            if not v.replace('/', '').isalnum():
                return v

            if '/' in v:
                v1, v2 = v.split('/')[:2]
                try:
                    return int(v1), int(v2)
                except:
                    return v
            else:
                return v

        if ',' in value:
            value = value.split(',')
            value = [ str_to_tuple(v) for v in value if v]
        else:
            value = str_to_tuple(value)

        return value


    @staticmethod
    def for_human(value, func=None):
        if type(value) in (tuple, list) and len(value)==2:
            x, y = value
            try:
                float(x), float(y)
            except:
                return '-'.join([x,y])
            try:
                value = float(x)/y
            except ZeroDivisionError:
                value = 0
            if value < 1:
                value = '%s/%s' % (x, y)
            else:
                value = round(value, 1)

        if func is not None:
            try: value = func(value)
            except: pass
        return value

