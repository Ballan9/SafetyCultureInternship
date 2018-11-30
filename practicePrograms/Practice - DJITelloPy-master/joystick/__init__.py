import os.path
from kivy.resources import resource_add_path
from kivy.lang import Builder

KV_PATH = os.path.realpath(os.path.dirname(__file__))
resource_add_path(KV_PATH)

Builder.load_file("joystickpad.kv")
Builder.load_file("joystick.kv")
