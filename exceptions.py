
class DataStructureError(Exception):

    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class HandSortError(KeyError):

    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class ReadingConstructionError(Exception):

    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)
