import sys
import traceback
import tellopy
import time
from subprocess import Popen, PIPE

video_output = None


def videoFrameHandler(event, sender, data):
    global video_output
    if video_output is None:
        cmd = [ 'ffmpeg', '-i', 'pipe:', 'Output.mp4' ]
        video_output = Popen(cmd, stdin=PIPE)

    try:
        video_output.stdin.write(data)
    except IOError as err:
        # status_print(str(err))
        video_output = None
        # throw(err)


def main():
    drone = tellopy.Tello()

    try:
        drone.connect()
        drone.wait_for_connection(60.0)

        drone.start_video()
        drone.subscribe(drone.EVENT_VIDEO_FRAME, videoFrameHandler)
        while 1:
                print("Running...")
    except Exception as ex:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback)
        print(ex)
    finally:
        drone.quit()

if __name__ == '__main__':
    main()