# coding: utf8
import traceback, sys
import datetime
from io import StringIO




def capture_error(exc_info=None): # 本身不要再引发错误
    f = None
    try:
        error_info = exc_info or sys.exc_info()
        if error_info:
            f = StringIO()
            e_type, value, tb = error_info[:3]
            try:
                # 错误信息保存到本地
                now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                f.write(now + "\n")
                traceback.print_exception(e_type, value, tb, file=f)
            except:
                pass
    except:
        pass
    if f:
        f.close()
        return f.getvalue()
    else:
        return ""