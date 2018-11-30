"""Error types for tellopy"""


class Tello_Error(Exception):
    """Base class for all Tello errors"""

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return '%s : :%s' % (self.__class__.__name__, self.message)

    def __repr__(self):
        return self.__str__()
