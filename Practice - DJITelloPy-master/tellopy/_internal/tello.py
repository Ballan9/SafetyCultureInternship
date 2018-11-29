import threading
import socket
import time
from . import logger
from . import event
from . import state
from . import error
from . import video_stream
from . protocol import *
from . import dispatcher

log = logger.Logger('Tello')


class Tello(object):
    EVENT_CONNECTED = event.Event('Connected')
    EVENT_WIFI = event.Event('Wi-fi')
    EVENT_LIGHT = event.Event('Light')
    EVENT_FLIGHT_DATA = event.Event('Flight data')
    EVENT_LOG = event.Event('Log')
    EVENT_TIME = event.Event('Time')
    EVENT_VIDEO_FRAME = event.Event('Video frame')
    EVENT_VIDEO_DATA = event.Event('Video data')
    EVENT_DISCONNECTED = event.Event('Disconnected')
    # internal events
    __EVENT_CONN_REQ = event.Event('Connection required')
    __EVENT_CONN_ACK = event.Event('Conn acknowledged')
    __EVENT_TIMEOUT = event.Event('Time-out')
    __EVENT_QUIT_REQ = event.Event('Quit required')

    # for backward compatibility
    CONNECTED_EVENT = EVENT_CONNECTED
    WIFI_EVENT = EVENT_WIFI
    LIGHT_EVENT = EVENT_LIGHT
    FLIGHT_EVENT = EVENT_FLIGHT_DATA
    LOG_EVENT = EVENT_LOG
    TIME_EVENT = EVENT_TIME
    VIDEO_FRAME_EVENT = EVENT_VIDEO_FRAME

    STATE_DISCONNECTED = state.State('Disconnected')
    STATE_CONNECTING = state.State('Connecting')
    STATE_CONNECTED = state.State('Connected')
    STATE_QUIT = state.State('Quit')

    LOG_ERROR = logger.LOG_ERROR
    LOG_WARN = logger.LOG_WARN
    LOG_INFO = logger.LOG_INFO
    LOG_DEBUG = logger.LOG_DEBUG
    LOG_ALL = logger.LOG_ALL

    def __init__(self, port=9000):
        self.tello_addr = ('192.168.10.1', 8889)  # IP address as stated in Tello DJI manual
        self.debug = False
        self.pkt_seq_num = 0x01e4
        self.port = port
        self.udpsize = 2000  # User datagram protocol (UDP)
        self.left_x = 0.0
        self.left_y = 0.0
        self.right_x = 0.0
        self.right_y = 0.0
        self.sock = None
        self.state = self.STATE_DISCONNECTED
        self.lock = threading.Lock()
        self.connected = threading.Event()
        self.video_enabled = False
        self.prev_video_data_time = None
        self.video_data_size = 0
        self.video_data_loss = 0
        self.log = log
        self.exposure = 0
        self.video_encoder_rate = 4
        self.video_stream = None

        # Create a UDP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('', self.port))
        self.sock.settimeout(2.0)

        dispatcher.connect(self.__state_machine, dispatcher.signal.All)
        threading.Thread(target=self.__recv_thread).start()
        threading.Thread(target=self.__video_thread).start()

    def set_loglevel(self, level):
        """
        Set_loglevel controls the output messages. Valid levels are
        LOG_ERROR, LOG_WARN, LOG_INFO, LOG_DEBUG and LOG_ALL.
        """
        log.set_level(level)

    def get_video_stream(self):
        """
        Get_video_stream is used to prepare buffer object which receive video data from the drone.
        """
        newly_created = False
        self.lock.acquire()
        log.info('Get video stream')
        try:
            if self.video_stream is None:
                self.video_stream = video_stream.VideoStream(self)
                newly_created = True
            res = self.video_stream
        finally:
            self.lock.release()
        if newly_created:
            self.__send_exposure()
            self.__send_video_encoder_rate()
            self.start_video()

        return res

    def connect(self):
        """Connect is used to send the initial connection request to the drone."""
        self.__publish(event=self.__EVENT_CONN_REQ)

    def wait_for_connection(self, timeout=None):
        """Wait_for_connection will block until the connection is established."""
        if not self.connected.wait(timeout):
            raise error.TelloError('Timeout')

    def __send_conn_req(self):
        port = 9617
        port0 = (int(port/1000) % 10) << 4 | (int(port/100) % 10)
        port1 = (int(port/10) % 10) << 4 | (int(port/1) % 10)
        buf = 'conn_req:%c%c' % (chr(port0), chr(port1))
        log.info('Send connection request (Command = "%s%02x%02x")' % (str(buf[:-2]), port0, port1))
        return self.send_packet(Packet(buf))

    def subscribe(self, signal, handler):
        """Subscribe a event such as EVENT_CONNECTED, EVENT_FLIGHT_DATA, EVENT_VIDEO_FRAME and so on."""
        dispatcher.connect(handler, signal)

    def __publish(self, event, data=None, **args):
        args.update({'data': data})
        if 'signal' in args:
            del args['signal']
        if 'sender' in args:
            del args['sender']
        log.debug('Publish signal = %s, args = %s' % (event, args))
        dispatcher.send(event, sender=self, **args)

    def takeoff(self):
        """Take off tells the drones to liftoff and start flying."""
        log.info('Take off (command = 0x%02x sequence = 0x%04x)' % (TAKEOFF_CMD, self.pkt_seq_num))
        pkt = Packet(TAKEOFF_CMD)
        pkt.fixup()
        return self.send_packet(pkt)

    def land(self):
        """Land tells the drone to come in for landing."""
        log.info('Land (command = 0x%02x sequence = 0x%04x)' % (LAND_CMD, self.pkt_seq_num))
        pkt = Packet(LAND_CMD)
        pkt.add_byte(0x00)
        pkt.fixup()
        return self.send_packet(pkt)

    def quit(self):
        """Quit stops the internal threads."""
        log.info('Quit')
        self.__publish(event=self.__EVENT_QUIT_REQ)

    def __send_time_command(self):
        log.info('Send time (command = 0x%02x sequence = 0x%04x)' % (TIME_CMD, self.pkt_seq_num))
        pkt = Packet(TIME_CMD, 0x50)
        pkt.add_byte(0)
        pkt.add_time()
        pkt.fixup()
        return self.send_packet(pkt)

    def __send_start_video(self):
        pkt = Packet(VIDEO_START_CMD, 0x60)
        pkt.fixup()
        return self.send_packet(pkt)

    def start_video(self):
        """Start video tells the drone to send start info (SPS/PPS) for video stream."""
        log.info('Start video (command = 0x%02x sequence = 0x%04x)' % (VIDEO_START_CMD, self.pkt_seq_num))
        self.video_enabled = True
        self.__send_exposure()
        self.__send_video_encoder_rate()
        return self.__send_start_video()

    def set_exposure(self, level):
        """Set exposure sets the drone camera exposure level. Valid levels are 0, 1, and 2."""
        if level < 0 or 2 < level:
            raise error.TelloError('Invalid exposure level')
        log.info('Set exposure (command = 0x%02x sequence = 0x%04x)' % (EXPOSURE_CMD, self.pkt_seq_num))
        self.exposure = level
        return self.__send_exposure()

    def __send_exposure(self):
        pkt = Packet(EXPOSURE_CMD, 0x48)
        pkt.add_byte(self.exposure)
        pkt.fixup()
        return self.send_packet(pkt)

    def set_video_encoder_rate(self, rate):
        """Set_video_encoder_rate sets the drone video encoder rate."""
        log.info('Set video encoder rate (command = 0x%02x sequence = 0x%04x)' %
                 (VIDEO_ENCODER_RATE_CMD, self.pkt_seq_num))
        self.video_encoder_rate = rate
        return self.__send_video_encoder_rate()

    def __send_video_encoder_rate(self):
        pkt = Packet(VIDEO_ENCODER_RATE_CMD, 0x68)
        pkt.add_byte(self.video_encoder_rate)
        pkt.fixup()
        return self.send_packet(pkt)

    def up(self, val):
        """Up tells the drone to ascend. Pass in an int from 0-100."""
        log.info('Up(value = %d)' % val)
        self.left_y = val / 100.0

    def down(self, val):
        """Down tells the drone to descend. Pass in an int from 0-100."""
        log.info('Down(value = %d)' % val)
        self.left_y = val / 100.0 * -1

    def forward(self, val):
        """Forward tells the drone to go forward. Pass in an int from 0-100."""
        log.info('Forward(value = %d)' % val)
        self.right_y = val / 100.0

    def backward(self, val):
        """Backward tells the drone to go in reverse. Pass in an int from 0-100."""
        log.info('Backward(value = %d)' % val)
        self.right_y = val / 100.0 * -1

    def right(self, val):
        """Right tells the drone to go right. Pass in an int from 0-100."""
        log.info('Right(val = %d)' % val)
        self.right_x = val / 100.0

    def left(self, val):
        """Left tells the drone to go left. Pass in an int from 0-100."""
        log.info('Left(value = %d)' % val)
        self.right_x = val / 100.0 * -1

    def clockwise(self, val):
        """
        Clockwise tells the drone to rotate in a clockwise direction.
        Pass in an int from 0-100.
        """
        log.info('Clockwise(value = %d)' % val)
        self.left_x = val / 100.0

    def counter_clockwise(self, val):
        """
        Anti-Clockwise tells the drone to rotate in a counter-clockwise direction.
        Pass in an int from 0-100.
        """
        log.info('Anti-clockwise(value = %d)' % val)
        self.left_x = val / 100.0 * -1

    def flip_forward(self):
        """Flip forward tells the drone to perform a forwards flip"""
        log.info('Flip forward (command = 0x%02x sequence = 0x%04x)' % (FLIP_CMD, self.pkt_seq_num))
        pkt = Packet(FLIP_CMD, 0x70)
        pkt.add_byte(flip_front)
        pkt.fixup()
        return self.send_packet(pkt)


    def flip_back(self):
        """Flip back tells the drone to perform a backwards flip"""
        log.info('Flip back (command = 0x%02x sequence = 0x%04x)' % (FLIP_CMD, self.pkt_seq_num))
        pkt = Packet(FLIP_CMD, 0x70)
        pkt.add_byte(flip_back)
        pkt.fixup()
        return self.send_packet(pkt)

    def flip_right(self):
        """Flip right tells the drone to perform a right flip"""
        log.info('Flip right (command = 0x%02x sequence = 0x%04x)' % (FLIP_CMD, self.pkt_seq_num))
        pkt = Packet(FLIP_CMD, 0x70)
        pkt.add_byte(flip_right)
        pkt.fixup()
        return self.send_packet(pkt)

    def flip_left(self):
        """Flip left tells the drone to perform a left flip"""
        log.info('Flip left (command = 0x%02x sequence = 0x%04x)' % (FLIP_CMD, self.pkt_seq_num))
        pkt = Packet(FLIP_CMD, 0x70)
        pkt.add_byte(flip_left)
        pkt.fixup()
        return self.send_packet(pkt)

    def flip_forwardleft(self):
        """Flip forward-left tells the drone to perform a forwards left flip"""
        log.info('Flip forward-left (command = 0x%02x sequence = 0x%04x)' % (FLIP_CMD, self.pkt_seq_num))
        pkt = Packet(FLIP_CMD, 0x70)
        pkt.add_byte(flip_forward_left)
        pkt.fixup()
        return self.send_packet(pkt)

    def flip_backleft(self):
        """Flip back-left tells the drone to perform a backwards left flip"""
        log.info('Flip back-left (command = 0x%02x sequence = 0x%04x)' % (FLIP_CMD, self.pkt_seq_num))
        pkt = Packet(FLIP_CMD, 0x70)
        pkt.add_byte(flip_back_left)
        pkt.fixup()
        return self.send_packet(pkt)

    def flip_forwardright(self):
        """Flip forward-right tells the drone to perform a forwards right flip"""
        log.info('Flip forward right (command = 0x%02x sequence = 0x%04x)' % (FLIP_CMD, self.pkt_seq_num))
        pkt = Packet(FLIP_CMD, 0x70)
        pkt.add_byte(flip_forward_right)
        pkt.fixup()
        return self.send_packet(pkt)

    def flip_backright(self):
        """Flip back-left tells the drone to perform a backwards right flip"""
        log.info('Flip back-right (command = 0x%02x sequence = 0x%04x)' % (FLIP_CMD, self.pkt_seq_num))
        pkt = Packet(FLIP_CMD, 0x70)
        pkt.add_byte(flip_back_left)
        pkt.fixup()
        return self.send_packet(pkt)

    def __fix_range(self, val, minimum=-1.0, maximum=1.0):
        if val < minimum:
            val = minimum
        elif val > maximum:
            val = maximum
        return val

    def set_throttle(self, throttle):
        """
        Set throttle controls the vertical up and down motion of the drone.
        Pass in an int from -1.0 ~ 1.0. (positive value means upward)
        """
        if self.left_y != self.__fix_range(throttle):
            log.info('Set throttle(value = %4.2f)' % throttle)
        self.left_y = self.__fix_range(throttle)

    def set_yaw(self, yaw):
        """
        Set yaw (yaw is the slight movement of left to right of its intended direction)
        controls the left and right rotation of the drone.
        Pass in an int from -1.0 ~ 1.0. (positive value will make the drone turn to the right)
        """
        if self.left_x != self.__fix_range(yaw):
            log.info('Set yaw(value = %4.2f)' % yaw)
        self.left_x = self.__fix_range(yaw)

    def set_pitch(self, pitch):
        """
        Set pitch controls the forward and backward tilt of the drone.
        Pass in an int from -1.0 ~ 1.0. (positive value will make the drone move forward)
        """
        if self.right_y != self.__fix_range(pitch):
            log.info('Set pitch(value = %4.2f)' % pitch)
        self.right_y = self.__fix_range(pitch)

    def set_roll(self, roll):
        """
        Set roll controls the the side to side tilt of the drone.
        Pass in an int from -1.0 ~ 1.0. (positive value will make the drone move to the right)
        """
        if self.right_x != self.__fix_range(roll):
            log.info('Set roll(value = %4.2f)' % roll)
        self.right_x = self.__fix_range(roll)

    def __send_stick_command(self):
        pkt = Packet(STICK_CMD, 0x60)
        axis1 = int(1024 + 660.0 * self.right_x) & 0x7ff
        axis2 = int(1024 + 660.0 * self.right_y) & 0x7ff
        axis3 = int(1024 + 660.0 * self.left_y) & 0x7ff
        axis4 = int(1024 + 660.0 * self.left_x) & 0x7ff
        """
        11 bits (-1024 ~ +1023) x 4 axis = 44 bits
        44 bits will be packed in to 6 bytes (48 bits)

                    axis4      axis3      axis2      axis1
             |          |          |          |          |
                 4         3         2         1         0
        98765432109876543210987654321098765432109876543210
         |       |       |       |       |       |       |
             byte5   byte4   byte3   byte2   byte1   byte0
        """
        log.debug("Stick command: yaw = %4d throttle = %4d pitch = %4d roll = %4d" %
                  (axis4, axis3, axis2, axis1))
        log.debug("Stick command: yaw = %04x throttle = %04x pitch = %04x roll = %04x" %
                  (axis4, axis3, axis2, axis1))
        pkt.add_byte(((axis2 << 11 | axis1) >> 0) & 0xff)
        pkt.add_byte(((axis2 << 11 | axis1) >> 8) & 0xff)
        pkt.add_byte(((axis3 << 11 | axis2) >> 5) & 0xff)
        pkt.add_byte(((axis4 << 11 | axis3) >> 2) & 0xff)
        pkt.add_byte(((axis4 << 11 | axis3) >> 10) & 0xff)
        pkt.add_byte(((axis4 << 11 | axis3) >> 18) & 0xff)
        pkt.add_time()
        pkt.fixup()
        log.debug("Stick command: %s" % byte_to_hexstring(pkt.get_buffer()))
        return self.send_packet(pkt)

    def send_packet(self, pkt):
        """Send packet is used to send a command packet to the drone."""
        try:
            cmd = pkt.get_buffer()
            self.sock.sendto(cmd, self.tello_addr)
            log.debug("Send packet: %s" % byte_to_hexstring(cmd))
        except socket.error as err:
            if self.state == self.STATE_CONNECTED:
                log.error("Send packet: %s" % str(err))
            else:
                log.info("Send packet: %s" % str(err))
            return False

        return True

    def __process_packet(self, data):
        if isinstance(data, str):
            data = bytearray([x for x in data])

        if str(data[0:9]) == 'Connect acknowledged:' or data[0:9] == b'conn_ack:':
            log.info('Connected. (Port = %2x%2x)' % (data[9], data[10]))
            log.debug('    %s' % byte_to_hexstring(data))
            if self.video_enabled:
                self.__send_exposure()
                self.__send_video_encoder_rate()
                self.__send_start_video()
            self.__publish(self.__EVENT_CONN_ACK, data)

            return True

        if data[0] != START_OF_PACKET:
            log.info('Start of packet not %02x (%02x) (ignored)' % (START_OF_PACKET, data[0]))
            log.info('    %s' % byte_to_hexstring(data))
            log.info('    %s' % str(map(chr, data))[1:-1])
            return False

        pkt = Packet(data)
        cmd = int16(data[5], data[6])
        if cmd == LOG_MSG:
            log.debug("Received: Log: %s" % byte_to_hexstring(data[9:]))
            self.__publish(event=self.EVENT_LOG, data=data[9:])
        elif cmd == WIFI_MSG:
            log.debug("Received: Wi-Fi: %s" % byte_to_hexstring(data[9:]))
            self.__publish(event=self.EVENT_WIFI, data=data[9:])
        elif cmd == LIGHT_MSG:
            log.debug("Received: Light: %s" % byte_to_hexstring(data[9:]))
            self.__publish(event=self.EVENT_LIGHT, data=data[9:])
        elif cmd == FLIGHT_MSG:
            flight_data = FlightData(data[9:])
            log.debug("Received: Flight data: %s" % str(flight_data))
            self.__publish(event=self.EVENT_FLIGHT_DATA, data=flight_data)
        elif cmd == TIME_CMD:
            log.debug("Received: Time data: %s" % byte_to_hexstring(data))
            self.__publish(event=self.EVENT_TIME, data=data[7:9])
        elif (TAKEOFF_CMD, LAND_CMD, VIDEO_START_CMD, VIDEO_ENCODER_RATE_CMD):
            log.info("Received: acknowledged: command = 0x%02x sequence = 0x%04x %s" %
                     (int16(data[5], data[6]), int16(data[7], data[8]), byte_to_hexstring(data)))
        else:
            log.info('Unknown packet: %s' % byte_to_hexstring(data))
            return False

        return True

    def __state_machine(self, event, sender, data, **args):
        self.lock.acquire()
        cur_state = self.state
        event_connected = False
        event_disconnected = False
        log.debug('Event %s in state %s' % (str(event), str(self.state)))

        if self.state == self.STATE_DISCONNECTED:
            if event == self.__EVENT_CONN_REQ:
                self.__send_conn_req()
                self.state = self.STATE_CONNECTING
            elif event == self.__EVENT_QUIT_REQ:
                self.state = self.STATE_QUIT
                event_disconnected = True
                self.video_enabled = False

        elif self.state == self.STATE_CONNECTING:
            if event == self.__EVENT_CONN_ACK:
                self.state = self.STATE_CONNECTED
                event_connected = True
                # send time
                self.__send_time_command()
            elif event == self.__EVENT_TIMEOUT:
                self.__send_conn_req()
            elif event == self.__EVENT_QUIT_REQ:
                self.state = self.STATE_QUIT

        elif self.state == self.STATE_CONNECTED:
            if event == self.__EVENT_TIMEOUT:
                self.__send_conn_req()
                self.state = self.STATE_CONNECTING
                event_disconnected = True
                self.video_enabled = False
            elif event == self.__EVENT_QUIT_REQ:
                self.state = self.STATE_QUIT
                event_disconnected = True
                self.video_enabled = False

        elif self.state == self.STATE_QUIT:
            pass

        if cur_state != self.state:
            log.info('State transit %s -> %s' % (cur_state, self.state))
        self.lock.release()

        if event_connected:
            self.__publish(event=self.EVENT_CONNECTED, **args)
            self.connected.set()
        if event_disconnected:
            self.__publish(event=self.EVENT_DISCONNECTED, **args)
            self.connected.clear()

    def __recv_thread(self):
        sock = self.sock

        while self.state != self.STATE_QUIT:

            if self.state == self.STATE_CONNECTED:
                self.__send_stick_command()  # ignore errors

            try:
                data, server = sock.recvfrom(self.udpsize)
                log.debug("Received: %s" % byte_to_hexstring(data))
                self.__process_packet(data)
            except socket.timeout as ex:
                if self.state == self.STATE_CONNECTED:
                    log.error('Received: Timeout')
                self.__publish(event=self.__EVENT_TIMEOUT)
            except Exception as ex:
                log.error('Received: %s' % str(ex))
                show_exception(ex)

        log.info('Exit from the Received thread.')

    def __video_thread(self):
        log.info('Start video thread')
        # Create a UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        port = 6038
        sock.bind(('', port))
        sock.settimeout(5.0)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 512 * 1024)
        log.info('Video receive buffer size = %d' %
                 sock.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF))

        prev_header = None
        prev_ts = None
        history = []
        while self.state != self.STATE_QUIT:
            if not self.video_enabled:
                time.sleep(1.0)
                continue
            try:
                data, server = sock.recvfrom(self.udpsize)
                now = datetime.datetime.now()
                log.debug("Video received: %s %d bytes" % (byte_to_hexstring(data[0:2]), len(data)))
                show_history = False

                # check video data loss
                header = byte(data[0])
                if (prev_header is not None and
                    header != prev_header and
                    header != ((prev_header + 1) & 0xff)):
                    loss = header - prev_header
                    if loss < 0:
                        loss = loss + 256
                    self.video_data_loss += loss
                    #
                    # enable this line to see packet history
                    # show_history = True
                    #
                prev_header = header

                # check video data interval
                if prev_ts is not None and 0.1 < (now - prev_ts).total_seconds():
                    log.info('Video Received: %d bytes %02x%02x +%03d' %
                             (len(data), byte(data[0]), byte(data[1]),
                              (now - prev_ts).total_seconds() * 1000))
                prev_ts = now

                # save video data history
                history.append([now, len(data), byte(data[0])*256 + byte(data[1])])
                if 100 < len(history):
                    history = history[1:]

                # show video data history
                if show_history:
                    prev_ts = history[0][0]
                    for i in range(1, len(history)):
                        [ ts, sz, sn ] = history[i]
                        print('    %02d:%02d:%02d.%03d %4d bytes %04x +%03d%s' %
                              (ts.hour, ts.minute, ts.second, ts.microsecond/1000,
                               sz, sn, (ts - prev_ts).total_seconds()*1000,
                               (' *' if i == len(history) - 1 else '')))
                        prev_ts = ts
                    history = history[-1:]

                # deliver video frame to subscribers
                self.__publish(event=self.EVENT_VIDEO_FRAME, data=data[2:])
                self.__publish(event=self.EVENT_VIDEO_DATA, data=data)

                # show video frame statistics
                if self.prev_video_data_time is None:
                    self.prev_video_data_time = now
                self.video_data_size += len(data)
                dur = (now - self.prev_video_data_time).total_seconds()
                if 2.0 < dur:
                    log.info(('Video data %d bytes %5.1fKB/sec' %
                              (self.video_data_size, self.video_data_size / dur / 1024)) +
                             ((' Loss = %d' % self.video_data_loss) if self.video_data_loss != 0 else ''))
                    self.video_data_size = 0
                    self.prev_video_data_time = now
                    self.video_data_loss = 0

                    # keep sending start video command
                    self.__send_start_video()

            except socket.timeout as ex:
                log.error('Video received: Timeout')
                data = None
            except Exception as ex:
                log.error('Video received: %s' % str(ex))
                show_exception(ex)

        log.info('Exit from the video thread.')


if __name__ == '__main__':
    print('You can use test.py for testing.')