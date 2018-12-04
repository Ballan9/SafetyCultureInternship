# The Great Datb
# Create image recognition of assets ie fire extinguishers through the use of drones.
#
* How to install *

1.Clone repo

2. Go into interns\workingOnPrograms\TelloSDKPy
3. pip install requirements.txt or install each of the packages from requirements.txt

4. Run example.py 
  *example.py has a few functions that are commented out as I am still trying to get the livestream and record going. The live stream and record from my laptop webcam works. But i struggle to get the decoding done right. 

This repo consists of a few different collections of repos that are able to control the drone and streams video back onto your pc
The goBot folder is all written in go, due to my lack of previous knowledge of working with go I could not figure out how to get the streaming to pc service working. 

The TelloPy is a Repo cloned from https://github.com/hanyazou/TelloPy (Go to this repo for in depth instructions of installing). It is a python program that runs controls and stream the video back to you computer. We have had trouble getting the AV package to install properly.

https://godoc.org/gobot.io/x/gobot/platforms/dji/tello- This has in depth source code for the bot written in go 

There is another repo found https://github.com/dji-sdk/Tello-Python/tree/master/Tello_Video/h264decoder which has an indepth gui that has camera feed. But requires AV and my pc wont import the AV package correctly

The best repo we have found atm is https://github.com/damiafuentes/DJITelloPy which has simple steps to install and has the live video streaming working. 
In TelloSDKPy folder you will find the example.py and exampleA.py The example.py works great just doesnt save the video. The exampleA.py is the program that I was fiddling with trying to get to save the live stream
