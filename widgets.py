import pygame


class toggleable:
    def __init__(self, name, width):
        self.name = name
        self.width = width
        self.myfont = pygame.font.SysFont("monospace", 16)
        self.state = False

    def render(self):
        if self.state:
            text = self.myfont.render(
                self.name + ": On", True, (0, 0, 0))  # black is (0,0,0)
        else:
            text = self.myfont.render(
                self.name + ": Off", True, (0, 0, 0))  # black is (0,0,0)
        # create a surface with height same as text height
        background = pygame.Surface((self.width, text.get_height()))
        background.fill(((not self.state) * 150, self.state * 150, 0))
        background.blit(text, (0, 0))
        return background

    def get_height(self):
        return self.myfont.get_height()

    def toggle(self):
        self.state = not self.state

    def enable(self):
        self.state = True

    def disable(self):
        self.state = False


class display:
    def __init__(self, name, width):
        self.name = name
        self.width = width
        self.myfont = pygame.font.SysFont("monospace", 16)
        self.value = 0
        self.bgcolor = (255, 255, 255)  # background color white (255,255,255)

    def render(self):
        text = self.myfont.render(
            self.name+": " + str(self.value), True, (0, 0, 0))
        background = pygame.Surface((self.width, text.get_height()))
        background.fill(self.bgcolor)
        background.blit(text, (0, 0))
        return background

    def get_height(self):
        return self.myfont.get_height()

    def setValue(self, value):
        self.value = value


class sliderdisplay:
    def __init__(self, name, width, height):
        self.name = name
        self.width = width
        self.height = height
        self.value = 0
        self.myfont = None

    def render(self):
        bar = pygame.Surface((self.width, self.height))
        bar.fill((230, 230, 230))  # slider display background

        # draw bar
        # print (self.value)
        if self.value < 0:
            bar.fill((70, 70, 240), (0, self.height*.5,
                     self.width, -self.value*self.height*.5))
        else:
            bar.fill((70, 70, 240), (0, (1-self.value)*self.height*.5,
                     self.width, self.value*self.height*.5))

        # draw tick marks
        for i in range(1, 10):  # prints 1,2,3,4,5,6,7,8,9,10
            pygame.draw.line(bar, (255, 0, 0), (0, self.height*i*.1),
                             # (255,0,0) is red
                             (self.width*.25, self.height*i*.1))
            pygame.draw.rect(bar, (255, 0, 0), pygame.Rect(
                0, 0, self.width, self.height), 2)  # outline bar graphs in red
        return bar
