import time
import traceback
import sys
from subprocess import Popen, PIPE

import cv2 as cv
import numpy as np
import pygame
from djitellopy import Tello
from pygame.locals import *

# Speed of the drone
S = 60
# Frames per second of the pygame window display
FPS = 25
# video_output = None



#
# def videoFrameHandler(event, sender, data):
#     global video_output
#     if video_output is None:
#         cmd = ['ffmpeg', '-i', 'pipe', 'tristan.mp4']
#         video_output = Popen(cmd, stdin=PIPE)
#
#     try:
#         video_output.stdin.write(data)
#     except IOError as err:
#         video_output = None

class FrontEnd(object):
    """ Maintains the Tello display and moves it through the keyboard keys.
        Press escape key to quit.
        The controls are:
            - T: Takeoff
            - L: Land
            - Arrow keys: Forward, backward, left and right.
            - A and D: Counter clockwise and clockwise rotations
            - W and S: Up and down.
    """



    def __init__(self):
        # Init pygame
        self.cv = cv.cv2
        pygame.init()
        # videoFrameHandler()

        # Creat pygame window

        pygame.display.set_caption("Tello video stream")
        self.screen = pygame.display.set_mode([960, 720])

        # Init Tello object that interacts with the Tello drone
        self.tello = Tello()



        # Drone velocities between -100~100
        self.for_back_velocity = 0
        self.left_right_velocity = 0
        self.up_down_velocity = 0
        self.yaw_velocity = 0
        self.speed = 10

        self.send_rc_control = False

        # create update timer
        pygame.time.set_timer(USEREVENT + 1, 50)



    def run(self):

        if not self.tello.connect():
            print("Tello not connected")
            return

        if not self.tello.set_speed(self.speed):
            print("Not set speed to lowest possible")
            return

        # In case streaming is on. This happens when we quit this program without the escape key.
        if not self.tello.streamoff():
            print("Could not stop video stream")
            return

        if not self.tello.streamon():
            print("Could not start video stream")
            return
        print("trying to recieve tello video to pygame")
        # frame_read = self.tello.get_frame_read()
        # print("got this tello frame and put it into pygame")

        should_stop = False
        while not should_stop:

            for event in pygame.event.get():
                if event.type == USEREVENT + 1:
                    self.update()
                elif event.type == QUIT:
                    should_stop = True
                elif event.type == KEYDOWN:
                    if event.key == K_ESCAPE:
                        should_stop = True
                    else:
                        self.keydown(event.key)
                elif event.type == KEYUP:
                    self.keyup(event.key)

            # if frame_read.stopped:
            #     frame_read.stop()
            #     break

            self.screen.fill([0, 0, 0])
            # frame = cv.cvtColor(frame_read.frame, cv.COLOR_BGR2RGB)
            # frame = np.rot90(frame)
            # frame = pygame.surfarray.make_surface(frame)



            cap = self.tello.get_video_capture()
            # define the codec and create VideoWriter object
            fourcc = cv.VideoWriter_fourcc(*'X264')
            out = cv.VideoWriter('myvideo.mp4', fourcc, 20.0, (640,480))
            codec = cv.CAP_PROP_FOURCC
            print(codec)
            while cap.isOpened():
                print("is opened")
                ret, frame = cap.read()
                if ret:
                    print("is ret")
                    frame = cv.flip(frame,90)
                    frame = np.rot90(frame)
                    frame = cv.cvtColor(frame, cv.COLOR_BGR2RGB)

                    frame = pygame.surfarray.make_surface(frame)
                    self.screen.blit(pygameFrame, (0, 0))
                    pygame.display.update()
                    print(frame)
                    # print(codec)

                    #write the flipped frame
                    out.write(frame)

                    # cv.imshow('frame',frame)
                    if cv.waitKey(1) & 0xFF == ord('q'):
                        break
                else:
                    break

            cap.release()
            out.release()
            cv.destroyAllWindows()


            time.sleep(1 / FPS)

        # Call it always before finishing. I deallocate resources.
        self.tello.end()


    def keydown(self, key):
        """ Update velocities based on key pressed
        Arguments:
            key: pygame key
        """
        if key == pygame.K_UP:  # set forward velocity
            self.for_back_velocity = S
        elif key == pygame.K_DOWN:  # set backward velocity
            self.for_back_velocity = -S
        elif key == pygame.K_LEFT:  # set left velocity
            self.left_right_velocity = -S
        elif key == pygame.K_RIGHT:  # set right velocity
            self.left_right_velocity = S
        elif key == pygame.K_w:  # set up velocity
            self.up_down_velocity = S
        elif key == pygame.K_s:  # set down velocity
            self.up_down_velocity = -S
        elif key == pygame.K_a:  # set yaw clockwise velocity
            self.yaw_velocity = -S
        elif key == pygame.K_d:  # set yaw counter clockwise velocity
            self.yaw_velocity = S

    def keyup(self, key):
        """ Update velocities based on key released
        Arguments:
            key: pygame key
        """
        if key == pygame.K_UP or key == pygame.K_DOWN:  # set zero forward/backward velocity
            self.for_back_velocity = 0
        elif key == pygame.K_LEFT or key == pygame.K_RIGHT:  # set zero left/right velocity
            self.left_right_velocity = 0
        elif key == pygame.K_w or key == pygame.K_s:  # set zero up/down velocity
            self.up_down_velocity = 0
        elif key == pygame.K_a or key == pygame.K_d:  # set zero yaw velocity
            self.yaw_velocity = 0
        elif key == pygame.K_t:  # takeoff
            self.tello.takeoff()
            self.send_rc_control = True
        elif key == pygame.K_l:  # land
            self.tello.land()
            self.send_rc_control = False

    def update(self):
        """ Update routine. Send velocities to Tello."""
        if self.send_rc_control:
            self.tello.send_rc_control(self.left_right_velocity, self.for_back_velocity, self.up_down_velocity,
                                       self.yaw_velocity)


def main():

        frontend = FrontEnd()
        frontend.run()


# run frontend
#         try:
#             frontend.run()
#             while 1:
#                     print("Running...")
#         except Exception as ex:
#             exc_type, exc_value, exc_traceback = sys.exc_info()
#             traceback.print_exception(exc_type, exc_value, exc_traceback)
#             print(ex)


if __name__ == '__main__':
    main()