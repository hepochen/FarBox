# coding: utf8
import traceback, sys





def print_error(exc_info=None): # 本身不要再引发错误
    f = None
    try:
        error_info = exc_info or sys.exc_info()
        if error_info:
            e_type, value, tb = error_info[:3]
            try:
                traceback.print_exception(e_type, value, tb)
            except:
                pass
    except:
        pass