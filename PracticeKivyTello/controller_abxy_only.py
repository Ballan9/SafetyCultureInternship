import pygame

pygame.init()

white = (255, 255, 255, 0)  # (R.G.B) cursor
black = (1, 1, 1, 0)  # background


def main():
    screen = pygame.display.set_mode((1300, 650))  # size of display screen
    pygame.display.set_caption("Joystick Testing / Xbox 360 Controller")
    pygame.display.update()
    game_exit = False
    lead_x = 300
    lead_y = 300

    joysticks = []
    clock = pygame.time.Clock()

    # for all the connected joysticks
    for i in range(0, pygame.joystick.get_count()):
        # create an Joystick object in our list
        joysticks.append(pygame.joystick.Joystick(i))
        # initialize them all (-1 means loop forever)
        joysticks[-1].init()
        # print a statement telling what the name of the controller is
        print("Detected joystick '", joysticks[-1].get_name(), "'")
    while not game_exit:
        clock.tick(60)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:  # quite event
                game_exit = True
        if event.type == pygame.JOYBUTTONDOWN:
            if event.button == 3:
                lead_y -= 10  # (3) Y = Up
            elif event.button == 0:
                lead_y += 10  # (0) A = Down
            elif event.button == 2:
                lead_x -= 10  # (2) X = Left
            else:
                lead_x += 10  # (1) B = Right

        screen.fill(black)

        pygame.draw.rect(screen, white, [lead_x, lead_y, 20, 20])

        pygame.display.update()
    pygame.quit()


main()
