import datetime
import threading

LOG_ERROR = 0
LOG_WARN = 1
LOG_INFO = 2
LOG_DEBUG = 3
LOG_ALL = 99


class Logger:
    def __init__(self, header=''):
        self.log_level = LOG_INFO
        self.header_string = header
        self.lock = threading.Lock()

    def header(self):
        now = datetime.datetime.now()
        time_stamp = ("%02d : %02d : %02d.%03d" % (now.hour, now.minute, now.second, now.microsecond/1000))
        return "%s : %s" % (self.header_string, time_stamp)

    def set_level(self, level):
        self.log_level = level

    def output(self, message):
        self.lock.acquire()
        print(message)
        self.lock.release()

    def error(self, detail):
        if self.log_level < LOG_ERROR:
            return
        self.output("%s :  ERROR : %s" % (self.header(), detail))

    def warn(self, detail):
        if self.log_level < LOG_WARN:
            return
        self.output("%s :  WARNING : %s" % (self.header(), detail))

    def info(self, detail):
        if self.log_level < LOG_INFO:
            return
        self.output("%s :  INFORMATION : %s" % (self.header(), detail))

    def debug(self, detail):
        if self.log_level < LOG_DEBUG:
            return
        self.output("%s :  DEBUG : %s" % (self.header(), detail))


if __name__ == '__main__':
    log = Logger('TEST')
    log.error('This is an ERROR message')
    log.warn('This is a WARNING message')
    log.info('This is an INFORMATION message')
    log.debug('This should ** NOT **  be displayed')
    log.set_level(LOG_ALL)
    log.debug('This is a DEBUG message')
