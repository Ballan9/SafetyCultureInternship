# Touch data - the coordinates of points where you are touching


class TouchData:
    x_distance = None
    y_distance = None
    x_offset = None
    y_offset = None
    relative_distance = None
    is_external = None
    in_range = None

    def __init__(self, joystick, touch):
        self.joystick = joystick
        self.touch = touch
        self._calculate()

    def _calculate(self):
        screen_joystick = self.joystick
        touch = self.touch
        x_distance = screen_joystick.center_x - touch.x
        y_distance = screen_joystick.center_y - touch.y
        x_offset = touch.x - screen_joystick.center_x
        y_offset = touch.y - screen_joystick.center_y
        relative_distance = ((x_distance ** 2) + (y_distance ** 2)) ** 0.5
        is_external = relative_distance > screen_joystick._total_radius
        in_range = relative_distance <= screen_joystick._radius_difference
        self._update(x_distance, y_distance, x_offset, y_offset, relative_distance, is_external, in_range)

    def _update(self, x_distance, y_distance, x_offset, y_offset,
                relative_distance, is_external, in_range):
        self.x_distance = x_distance
        self.y_distance = y_distance
        self.x_offset = x_offset
        self.y_offset = y_offset
        self.relative_distance = relative_distance
        self.is_external = is_external
        self.in_range = in_range
