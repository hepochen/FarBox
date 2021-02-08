# coding: utf8
from __future__ import absolute_import
from farbox_bucket.utils import to_int, to_float, get_value_from_data, smart_str, smart_unicode
from farbox_bucket.server.utils.site_resource import just_get_site_config
import datetime


class Date(object):
    def __init__(self, core):
        self.core = core

    def __getattr__(self, item):
        return getattr(self.core, item)

    def __getitem__(self, item):
        # 这样就可以允许用户直接 post.date['%Y-%m']
        if isinstance(item, (unicode, str)):
            return self.format(item)
        else:
            return self.__repr__()

    def __call__(self, *args, **kwargs):
        # 这样就可以允许用户直接 post.date('%Y-%m')
        if len(args) and isinstance(args[0], (str, unicode)):
            return self.format(args[0])
        return self.__repr__()


    def __gt__(self, other):
        if hasattr(other, 'core'):
            other = other.core
        return self.core > other

    def __ge__(self, other):
        if hasattr(other, 'core'):
            other = other.core
        return self.core >= other

    def __lt__(self, other):
        if hasattr(other, 'core'):
            other = other.core
        return self.core < other

    def __le__(self, other):
        if hasattr(other, 'core'):
            other = other.core
        return self.core <= other
    
    def __eq__(self, other):
        if hasattr(other, 'core'):
            other = other.core
        return self.core == other


    def before(self, seconds):
        seconds = to_int(seconds, 0)
        return Date(self.core-datetime.timedelta(seconds=seconds))

    def after(self, seconds):
        seconds = to_int(seconds, 0)
        return Date(self.core+datetime.timedelta(seconds=seconds))

    def format(self, format_str='%H:%M / %d-%m-%Y'):
        if not isinstance(self.core, datetime.datetime):
            return self.core or '-'

        utc_offset = just_get_site_config('utc_offset')
        try:
            utc_offset = float(utc_offset)
        except:
            utc_offset = 8
        if utc_offset > 12 or utc_offset < -12:
            utc_offset = 8
        if utc_offset is None:
            utc_offset = 8 # default value

        if not isinstance(utc_offset, (int, float)):
            utc_offset = 8
        format_str = smart_str(format_str[:200]) # 可以处理中文等unicode字符
        date = self.core + datetime.timedelta(0, utc_offset*3600)

        date_year = date.year
        if date_year <= 1900:
            date = date.replace(year=1900)
            result = date.strftime(format_str)
            result = result.replace('1900', str(date_year), 1)
        else:
            result = date.strftime(format_str)
        return smart_unicode(result)

    def __repr__(self):
        return self.format('%Y-%m-%d %H:%M')