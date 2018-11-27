from time import sleep
import tellopy
from subprocess import Popen, PIPE

video_output = None


def handler(event, sender, data, **args):
    drone = sender
    if event is drone.EVENT_FLIGHT_DATA:
        print(data)

def videoFrameHandler(event, sender, data):
    global video_output
    if video_output is None:
        cmd = [ 'ffmpeg', '-i', 'pipe:', 'output.mp4' ]
        video_output = Popen(cmd, stdin=PIPE)

    try:
        video_output.stdin.write(data)
    except IOError as err:
        # status_print(str(err))
        video_output = None
        # throw(err)

def test():
    drone = tellopy.Tello()
    try:

        drone.connect()
        drone.wait_for_connection(60.0)
        drone.takeoff()
        drone.start_video()

        drone.subscribe(drone.EVENT_VIDEO_FRAME, videoFrameHandler)

        sleep(5)
        drone.down(50)
        sleep(5)
        drone.land()
        sleep(5)
    except Exception as ex:
        print(ex)
    finally:
        drone.quit()


if __name__ == '__main__':

    test()
