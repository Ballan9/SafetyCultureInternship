class Event:
    def __init__(self, name="Anonymous"):
        self.name = name

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return '%s : : %s' % (self.__class__.__name__, self.name)

    def get_name(self):
        return self.name


if __name__ == '__main__':
    ev = Event()
    print(ev)
    ev = Event("Test event")
    print(ev)
