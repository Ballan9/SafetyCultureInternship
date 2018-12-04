import time
import threading

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

CONFIG_FILE = "yolov3.cfg"
# download this file from: https://pjreddie.com/media/files/yolov3.weights
WEIGHTS_FILE = "yolov3.weights"
CLASSES_FILE = "yolov3.classes"

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
        cap = self.tello.get_video_capture()

        classes = None
        with open(CLASSES_FILE, 'r') as f:
            classes = [line.strip() for line in f.readlines()]

        # define the codec and create VideoWriter object
        scale = 0.00392
        fourcc = cv.VideoWriter_fourcc(*'MP4V')
        out = cv.VideoWriter('myvideo.mp4', fourcc, 1, (640, 480))
        net = cv.dnn.readNet(WEIGHTS_FILE, CONFIG_FILE)
        frameCounter = 0;

        while cap.isOpened() and not self.should_stop:
            ret, frame = cap.read()
            if ret:
                frameCounter += 1

                # Run analysis every second.
                if frameCounter%30 == 0:
                    blob = cv.dnn.blobFromImage(frame, scale, (416, 416), (0, 0, 0), True, crop=False)
                    net.setInput(blob)

                    frame = self.run_inference(net, frame, classes)

                    displayFrame = cv.flip(frame, 90)
                    displayFrame = np.rot90(displayFrame)
                    displayFrame = cv.cvtColor(displayFrame, cv.COLOR_BGR2RGB)

                    pygameFrame = pygame.surfarray.make_surface(displayFrame)
                    self.screen.blit(pygameFrame, (0, 0))
                    pygame.display.update()

                    frame = cv.resize(frame, (640, 480))
                    out.write(frame)

                if cv.waitKey(1) & 0xFF == ord('q'):
                    break
            else:
                break

        cap.release()
        out.release()
        cv.destroyAllWindows()

    def get_output_layers(self, net):
        layer_names = net.getLayerNames()
        output_layers = [layer_names[i[0] - 1] for i in net.getUnconnectedOutLayers()]
        return output_layers

    def draw_bounding_box(self, frame, classes, class_id, confidence, x, y, x_plus_w, y_plus_h):
        label = str(classes[class_id] + str(confidence))
        frame = cv.rectangle(frame, (x, y), (x_plus_w, y_plus_h), [255, 0, 0], 2)
        frame = cv.putText(frame, label, (x - 10, y - 10), cv.FONT_HERSHEY_SIMPLEX, 0.5, [255, 0, 0], 2)
        return frame

    def run_inference(self, net, frame, classes):
        Width = frame.shape[1]
        Height = frame.shape[0]

        # run inference through the network
        # and gather predictions from output layers
        outs = net.forward(self.get_output_layers(net))

        # initialization
        class_ids = []
        confidences = []
        boxes = []
        conf_threshold = 0.5
        nms_threshold = 0.4

        # for each detetion from each output layer
        # get the confidence, class id, bounding box params
        # and ignore weak detections (confidence < 0.5)
        for out in outs:
            for detection in out:
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]
                if confidence > 0.5:
                    center_x = int(detection[0] * Width)
                    center_y = int(detection[1] * Height)
                    w = int(detection[2] * Width)
                    h = int(detection[3] * Height)
                    x = center_x - w / 2
                    y = center_y - h / 2
                    class_ids.append(class_id)
                    confidences.append(float(confidence))
                    boxes.append([x, y, w, h])

        # apply non-max suppression
        indices = cv.dnn.NMSBoxes(boxes, confidences, conf_threshold, nms_threshold)

        # go through the detections remaining
        # after nms and draw bounding box
        for i in indices:
            i = i[0]
            box = boxes[i]
            x = box[0]
            y = box[1]
            w = box[2]
            h = box[3]

            frame = self.draw_bounding_box(frame, classes, class_ids[i], confidences[i], round(x), round(y), round(x + w), round(y + h))

        return frame


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