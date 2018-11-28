from kivy.app import App
from kivy.core.window import Window
from joystick import Joystick
from kivy.uix.boxlayout import BoxLayout
from kivy.core.window import Window
from tellopy import Tello
from subprocess import Popen, PIPE
import os

video_output = None

IDX_ROLL = 0
IDX_PITCH = 1
IDX_THR = 2
IDX_YAW = 3


class DragableJoystick(Joystick):
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.pos = touch.x-self.width/2, touch.y-self.height/2
            return super(DragableJoystick, self).on_touch_down(touch)


class KivyTelloRoot(BoxLayout):

    def __init__(self, drone=None, **kwargs):
        super(KivyTelloRoot, self).__init__(**kwargs)
        self.stick_data = [0.0] * 4
        Window.allow_vkeyboard = False
        self.ids.pad_left.ids.stick.bind(pad=self.on_pad_left)
        self.ids.pad_right.ids.stick.bind(pad=self.on_pad_right)
        self.ids.takeoff.bind(state=self.on_state_takeoff)
        self.ids.rotcw.bind(state=self.on_state_rotcw)
        self.ids.rotccw.bind(state=self.on_state_rotccw)
        self.ids.quit.bind(on_press=lambda x: self.stop())
        self.drone = drone
        self.drone.subscribe(self.drone.EVENT_FLIGHT_DATA, self.handler)
        self.drone.start_video()
        self.drone.subscribe(self.drone.EVENT_VIDEO_FRAME, self.handler)

    def handler(self, event, sender, data, **args):
        drone = sender
        if event is self.drone.EVENT_FLIGHT_DATA:
            print(data)
        elif event is self.drone.EVENT_VIDEO_FRAME:
            pass
        else:
            print(('event="%s" data=%s' % (event.getname(), str(data))))

    def on_state_takeoff(self, instance, value):
        if value == 'down':
            print('take off')
            self.drone.takeoff()
        else:
            print('land')
            self.drone.land()

    def on_state_rotcw(self, instance, value):
        if value == 'down':
            print('start cw')
            self.drone.clockwise(50)
        else:
            print('stop cw')
            self.drone.clockwise(0)

    def on_state_rotccw(self, instance, value):
        if value == 'down':
            print('start ccw')
            self.drone.counter_clockwise(50)
        else:
            print('stop ccw')
            self.drone.counter_clockwise(0)

    def on_pad_left(self, instance, value):
        x, y = value
        self.stick_data[IDX_YAW] = x
        self.stick_data[IDX_THR] = y

        # Label above the stick
        self.ids.pad_left.ids.label.text = \
            'THR: {0:f}\n' \
            'YAW: {1:f}'.format(self.stick_data[IDX_THR],
                                self.stick_data[IDX_YAW])

        # Set throttle and yaw to input values
        self.drone.set_throttle(self.stick_data[IDX_THR])
        self.drone.set_yaw(self.stick_data[IDX_YAW])

    def on_pad_right(self, instance, value):
        x, y = value
        self.stick_data[IDX_ROLL] = x
        self.stick_data[IDX_PITCH] = y

        # Label Above Stick
        self.ids.pad_right.ids.label.text = \
            'ROLL: {0:f}\n' \
            'PITCH: {1:f}'.format(self.stick_data[IDX_ROLL],
                                  self.stick_data[IDX_PITCH])

        # Set the values of roll and pitch to the input data
        self.drone.set_roll(self.stick_data[IDX_ROLL])
        self.drone.set_pitch(self.stick_data[IDX_PITCH])

    def stop(self):
        self.drone.quit()
        App.get_running_app().stop()


class KivyTelloApp(App):
    def __init__(self, drone=None, **kwargs):
        super(KivyTelloApp, self).__init__(**kwargs)
        self.drone = drone
        drone.subscribe(drone.EVENT_VIDEO_FRAME, videoframehandler)

    def build(self):
        return KivyTelloRoot(drone=self.drone)

    def on_pause(self):
        return True

    def on_stop(self):
        Window.close()


def videoframehandler(event, sender, data):
    global video_output
    if video_output is None:
        # file_name = str(GetNextFilePath('C:\\Users\\T\'uKeyan\\Documents\\interns2018\\KivyTello2'))
        cmd = ['ffmpeg', '-i', 'pipe:', '%s' % getnextfilepath('C:\\Users\\T\'uKeyan\\Documents\\interns2018\\KivyTello2')]
        # cmd = ['ffmpeg', '-i', 'pipe:', '-r', '1', '-f', 'image2', 'image-%2d.png']
        video_output = Popen(cmd, stdin=PIPE)
    try:
        video_output.stdin.write(data)
    except IOError as err:
        # status_print(str(err))
        video_output = None
        # throw(err)


def getnextfilepath(output_folder):
    dirArray = []
    for f in os.listdir(output_folder):
        dirArray.append(f)

    y = -1
    z = 0
    for x in dirArray:
        y += 1
        if "output" in dirArray[y]:
            z += 1
            output_file = ("output%s.mp4" % str(z + 1))
        elif z == 0:
            output_file = "output0.mp4"

    return output_file # Output the filename

if __name__ in ('__main__', '__android__'):
    drone = Tello()
    try:
        drone.connect()
        drone.wait_for_connection(60.0)
        KivyTelloApp(drone=drone).run()
    except Exception as ex:
        print(ex)
        drone.quit()
        Window.close()
        # exit(1)