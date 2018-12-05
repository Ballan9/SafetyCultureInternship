import argparse
import time
import threading


import cv2 as cv
import numpy as np
import pygame
from djitellopy import Tello
from pygame.locals import *
import imutils

# Speed of the drone
S = 60
# Frames per second of the pygame window display
FPS = 25
# video_output = None

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

        threading.Thread(target=self.runVideo).start()

        self.should_stop = False
        while not self.should_stop:

            for event in pygame.event.get():
                if event.type == USEREVENT + 1:
                    self.update()
                elif event.type == QUIT:
                    self.should_stop = True
                elif event.type == KEYDOWN:
                    if event.key == K_ESCAPE:
                        self.should_stop = True
                    else:
                        self.keydown(event.key)
                elif event.type == KEYUP:
                    self.keyup(event.key)

            self.screen.fill([0, 0, 0])

            time.sleep(1 / FPS)

        # Call it always before finishing. I deallocate resources.
        self.tello.end()


    def runVideo(self):
        print("starting video")
        # cap = self.tello.get_video_capture(args["video"])
        ap = argparse.ArgumentParser()
        ap.add_argument("-v", "--video", help="path to the video file")
        args = vars(ap.parse_args())
        cap = self.tello.get_video_capture()

        # define the codec and create VideoWriter object
        fourcc = cv.VideoWriter_fourcc(*'MP4V')
        out = cv.VideoWriter('myvideo.mp4', fourcc, 30.0, (640, 480))
        codec = cv.CAP_PROP_FOURCC
        print(codec)
        while cap.isOpened() and not self.should_stop:
            ret, frame = cap.read()
            status = "No Targets"
            if ret:
                frame = cv.flip(frame, 90)
                frame = np.rot90(frame)
                frame = cv.cvtColor(frame, cv.COLOR_BGR2RGB)

                #cover the frame to grayscale, blur it, and detect edges
                gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
                blurred = cv.GaussianBlur(gray, (7, 7), 0)
                edged = cv.Canny(blurred, 50, 150)

                #find contours in the edge map
                cnts = cv.findContours(edged.copy(), cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
                cnts = cnts[0] if imutils.is_cv2() else cnts [1]
                print("found contours")

                #loop over the contours
                for c in cnts:
                    #approx the contour
                    peri = cv.arcLength(c, True)
                    approx = cv.approxPolyDP(c, 0.02 * peri, True)

                    #ensure that the approx contour is "roughly" rectangular
                    if 4 <= len(approx) <= 6:
                        #compute the bounding box of the approximated contour and
                        #use the bounding box to compute the aspect ratio
                        (x, y, w, h) = cv.boundingRect(approx)
                        aspectRatio = w / float(h)

                        #compute the solidity of the original contour
                        area = cv.contourArea(c)
                        hullArea = cv.contourArea(cv.convexHull(c))
                        solidity = area / float(hullArea)

                        #compute whether or not the width and height, solidity, and
                        #aspect ratio of the contour falls within appropriate bounds
                        keepDims = w > 25 and h > 25
                        keepSolidity = solidity > 0.9
                        keepAspectRatio =   aspectRatio >= 0.8 and aspectRatio <= 1.2

                        #ensure that the contour passes all our test
                        if keepDims and keepSolidity and keepAspectRatio:
                            #draw an aoutline around teh target and update the status
                            # text
                            cv.drawContours(frame, [approx], -1, (0, 0, 255), 4)
                            status = "Target(s) Acquired"

                            #compute the center of the contour region and draw the
                            #crosshairs
                            M = cv.moments(approx)
                            (cX, cY) = (int(M["m10"] // M["m00"]), int(M["m01"] // M["m00"]))
                            (startX, endX) = (int(cX - (w * 0.15)), int(cX + (w * 0.15)))
                            (startY, endY) = (int(cY - (h * 0.15)), int(cY + (h * 0.15)))
                            cv.line(frame, (startX, cY), (endX, cY), (0, 0, 255), 3)
                            cv.line(frame, (cX, startY), (cX, endY), (0, 0, 255), 3)

                cv.putText(frame, status, (20, 30), cv.FONT_HERSHEY_SIMPLEX, 0.5,(0, 0, 255),2)



                pygameFrame = pygame.surfarray.make_surface(frame)
                self.screen.blit(pygameFrame, (0, 0))
                pygame.display.update()

                frame = cv.resize(frame, (640, 480))

                # write the flipped frame
                # frame = np.rot90(frame)
                frame = cv.flip(frame, 90)

                out.write(frame)

                # cv.imshow('frame',frame)
                if cv.waitKey(1) & 0xFF == ord('q'):
                    break
            else:
                break

        cap.release()
        out.release()
        cv.destroyAllWindows()





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

if __name__ == '__main__':
    main()