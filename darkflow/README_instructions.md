# Datb setup

Instructions for setting up our application on a Mac or Linux desktop

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. See deployment for notes on how to deploy the project on a live system.

### Prerequisites

Mac machine
Lots of dependancies, will sort later..


### Installing

Use this to place video in for object detection testing, this will run YOLO darknet currently and will not identify fire extinguishers.

Terminal:
$ ssh admin@192.168.14.121
	#password is password

$ cd darknet

$ python flow --model cfg/yolo.cfg --load bin/yolov2.weights --demo videofireextinguisher.mp4 --gpu 1.0 --saveVideo
	# videofireextinguisher.mp4 is subject to change, alter this to change video, when I 	allow you to add video to folder.
$ open video.avi
	# plays video, will test later to see if I can return it to your device 

$ exit
	# will terminate the session




Orrr

Terminal:
$ ssh admin@192.168.14.121
	#password is password

$ cd Documents/object-tracking-dlib/ 

$ object-tracking-dlib admin$ python track_object.py --prototxt mobilenet_ssd/MobileNetSSD_deploy.prototxt --model mobilenet_ssd/MobileNetSSD_deploy.caffemodel --video input/cat.mp4 --label cat --output output/cat_output.avi



## Authors

Daniel Gilbert
Allan Serrurier
Belle
Travis Wilson

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details

## Acknowledgments

Everyone at SafteyCulture <3

