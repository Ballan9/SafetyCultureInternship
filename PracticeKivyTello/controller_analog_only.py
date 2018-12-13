#!/usr/bin/env python
# Written by alex@nyrpnz.com March 14 2012
# Modified by brooks@skoorb.net November 12 2012
#
# Disable global warning, we need to store OPTS globally
# pylint: disable-msg=W0603
# https://gist.github.com/brookst/4071514


"""Joystick event echoer using Pygame."""

import pygame
from os import environ
from pygame.locals import QUIT, JOYBUTTONUP, JOYBUTTONDOWN, JOYAXISMOTION, JOYHATMOTION

OPTS = None
JOYSTICKS = []

X360_AXIS_IDS = {
    'LEFT_X': 0,
    'LEFT_Y': 1,
    'LEFT_TRIGGER': 2,
    'RIGHT_X': 3,
    'RIGHT_Y': 4,
    'RIGHT_TRIGGER': 5,
    'D_PAD_X': 6,
    'D_PAD_Y': 7,
}

X360_BUTTON_IDS = {
    'A': 0,
    'B': 1,
    'X': 2,
    'Y': 3,
    'L_BUMPER': 4,
    'R_BUMPER': 5,
    'BACK': 6,
    'START': 7,
    'GUIDE': 8,
    'L_STICK': 9,
    'R_STICK': 10,
}

X360_AXIS_NAMES = dict([(idn, name) for name, idn in X360_AXIS_IDS.items()])
X360_BUTTON_NAMES = dict([(idn, name) for name, idn in X360_BUTTON_IDS.items()])

AXIS_NAMES = X360_AXIS_NAMES
AXIS_IDS = X360_AXIS_IDS
BUTTON_NAMES = X360_BUTTON_NAMES
BUTTON_IDS = X360_BUTTON_IDS
HAT_NAMES = {}
HAT_IDS = {}


def proc_event(event):
    """Parse and act upon event"""
    if event.type == QUIT:
        print("Received event 'Quit', exiting.")
        exit(0)
    elif event.type == JOYAXISMOTION and OPTS.axis:
        print("Joystick '%s' axis %s value %0.3f" % (JOYSTICKS[event.joy].get_name(),
                                                     AXIS_NAMES[event.axis], event.value))
    elif event.type == JOYBUTTONDOWN and OPTS.button:
        print("Joystick '%s' button %s down." % (JOYSTICKS[event.joy].get_name(),
                                                 BUTTON_NAMES[event.button]))
    elif event.type == JOYBUTTONUP and OPTS.button:
        print("Joystick '%s' button %s up." % (JOYSTICKS[event.joy].get_name(),
                                               BUTTON_NAMES[event.button]))
    elif event.type == JOYHATMOTION and OPTS.hat:
        print("Joystick '%s' hat motion." % (JOYSTICKS[event.joy].get_name()))


def get_opts():
    """Parse command line options"""
    from argparse import ArgumentParser
    parser = ArgumentParser()
    arg = parser.add_argument
    arg('-a', '--axis', action='store_false', default=True, help="Omit axis messages")
    arg('-b', '--button', action='store_false', default=True, help="Omit button messages")
    arg('--hat', action='store_false', default=True, help="Omit hat messages")
    arg('-p', '--pprint', action='store_true', default=False, help="Pretty print out controller map")
    return parser.parse_args()


def main():
    """Prints joystick events to the terminal. Closes on ESC or QUIT."""
    # Set up
    global OPTS
    OPTS = get_opts()
    from pprint import pprint
    if OPTS.pprint:
        pprint(AXIS_NAMES)
        pprint(BUTTON_NAMES)

    # Don't use drivers we don't need
    environ["SDL_VIDEODRIVER"] = "dummy"
    environ["SDL_AUDIODRIVER"] = "dummy"
    pygame.init()

    clock = pygame.time.Clock()
    for i in range(0, pygame.joystick.get_count()):
        JOYSTICKS.append(pygame.joystick.Joystick(i))
        JOYSTICKS[-1].init()
        print("Detected joystick '%s'" % JOYSTICKS[-1].get_name())
    while 1:
        try:
            clock.tick(60)
            for event in pygame.event.get():
                proc_event(event)
        except KeyboardInterrupt:
            print("\n" "Interrupted")
            exit(0)


if __name__ == "__main__":
    main()
