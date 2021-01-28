# coding: utf8


class LazyDict(dict):
    # 非常有用的一个处理，可以让dict 之类的数据，可以直接调用 property 的写法
    def __getitem__(self, item):
        try:
            value = dict.__getitem__(self, item)
        except:
            value = LazyDict()
        return value

    def __getattr__(self, item):
        return self.__getitem__(item)

    def __repr__(self):
        return ''

    def __nonzero__(self):
        return 0
