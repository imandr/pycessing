import os
import six
import sys, numpy as np, time

#if "Apple" in sys.version:
#    if 'DYLD_FALLBACK_LIBRARY_PATH' in os.environ:
#        os.environ['DYLD_FALLBACK_LIBRARY_PATH'] += ':/usr/lib'
#        # (JDS 2016/04/15): avoid bug on Anaconda 2.3.0 / Yosemite

try:
    import pyglet
except ImportError as e:
    raise ImportError('''
    Cannot import pyglet.
    HINT: you can install pyglet directly via 'pip install pyglet'.
    But if you really just want to install all Gym dependencies and not have to think about it,
    'pip install -e .[all]' or 'pip install gym[all]' will do it.
    ''')

if True:
    try:
        from pyglet.gl import *
    except ImportError as e:
        raise ImportError('''
        Error occurred while running `from pyglet.gl import *`
        HINT: make sure you have OpenGL install. On Ubuntu, you can run 'apt-get install python-opengl'.
        If you're running on a server, you may need a virtual frame buffer; something like this should work:
        'xvfb-run -s \"-screen 0 1400x900x24\" python <your_script.py>'
        ''')



def get_display(spec):
    """Convert a display specification (such as :0) into an actual Display
    object.

    Pyglet only supports multiple Displays on Linux.
    """
    if spec is None:
        return None
    elif isinstance(spec, six.string_types):
        return pyglet.canvas.Display(spec)
    else:
        raise error.Error('Invalid display specification: {}. (Must be a string like :0 or None.)'.format(spec))


class Screen(object):
    def __init__(self, width, height, corner0, corner1, display=None, clear_color=(0,0,0,1)):
        display = get_display(display)

        self.width = width
        self.height = height
        self.window = pyglet.window.Window(width=width, height=height, display=display)
        self.window.on_close = self.window_closed_by_user
        self.isopen = True
        self.onetime_geoms = []
        self.clear_color = clear_color

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_PROGRAM_POINT_SIZE)
        #glPointSize(20.0)
        
        self.StrokeColor = (1,1,1,1)
        self.FillColor = (0.5, 0.5, 0.5, 1.0)
        self.StrokeWeight = 1.0
        
        self.C0 = corner0
        self.C1 = corner1
        self.X0, self.Y0 = corner0
        self.X1, self.Y1 = corner1
        self.ScaleX, self.ScaleY = self.width/(self.C1[0]-self.X0), self.height/(self.C1[1]-self.Y0)

    def start_frame(self):
        self.window.switch_to()
        self.window.dispatch_events()
        
    def clear(self):
        glClearColor(*self.clear_color)
        self.window.clear()
        
        
    def fill(self, v1, v2, v3, a=1.0):
        self.FillColor = (v1, v2, v3, a)
        
    def noFill(self):
        self.FillColor = None
    
    def stroke(self, v1, v2, v3, a=1.0):
        self.StrokeColor = (v1, v2, v3, a)
        
    def noStroke(self):
        self.StrokeColor = None
    
    def strokeWeight(self, x):
        self.StrokeWeight = x
        glPointSize(x)
        
    def scale2d(self, x, y):
        return (x-self.X0)*self.ScaleX, (y-self.Y0)*self.ScaleY
        
    def point(self, x, y=None):
        if self.StrokeColor is None:    return
        if isinstance(x, np.ndarray):
            x, y = x[:2]
        w, h = self.scale2d(x, y)
        glColor4f(*self.StrokeColor)
        glBegin(GL_POINTS) # draw point
        glVertex3f(w, h, 0)
        glEnd()
        
    def points(self, points):
        if self.StrokeColor is None:    return
        w, h = self.scale2d(points[:,0], points[:,1])
        wh = np.array((w, h)).T
        glColor4f(*self.StrokeColor)
        for i in range(0, len(wh), 100):
            batch = wh[i:i+100]
            glBegin(GL_POINTS) # draw point
            for p in batch:
                #print("Sim.points(): x,y=", x, y)
                x, y = p
                glVertex3f(x, y, 0)
            glEnd()

    def line(self, a0, a1, x1=None, y1=None):
        if self.StrokeColor is None:    return
        if isinstance(a0, np.ndarray):
            x0, y0 = a0
            x1, y1 = a1
        else:
            x0, y0 = a0, a1
        glBegin(GL_LINES)
        glColor4f(*self.StrokeColor)
        glVertex3f(x0, y0, 0)
        glVertex3f(x1, y1, 0)
        glEnd()
        
    def rect(self, p0, p1, p2=None, p3=None):
        if isinstance(p0, np.ndarray):
            c1, c2 = self.scale2d(p0[0], p0[1]), self.scale2d(p1[0], p1[1])
        else:
            c1 = self.scale2d(p0, p1)
            c2 = self.scale2d(p0+p2, p1+p3)
        #print("rect: c1,c2:", c1, c2)
        if self.FillColor is not None:
            #print("rect: fill color:", self.FillColor)
            glColor4f(*self.FillColor)
            glBegin(GL_QUADS)
            glVertex3f(c1[0], c1[1], 0)  # draw each vertex
            glVertex3f(c2[0], c1[1], 0)  # draw each vertex
            glVertex3f(c2[0], c2[1], 0)  # draw each vertex
            glVertex3f(c1[0], c2[1], 0)  # draw each vertex
            glEnd()
        if self.StrokeColor is not None:
            glColor4f(*self.StrokeColor)
            glBegin(GL_LINE_LOOP)
            glVertex3f(c1[0], c1[1], 0)  # draw each vertex
            glVertex3f(c2[0], c1[1], 0)  # draw each vertex
            glVertex3f(c2[0], c2[1], 0)  # draw each vertex
            glVertex3f(c1[0], c2[1], 0)  # draw each vertex
            glEnd()
            
        
    def end_frame(self):
        self.window.flip()
        
    def window_closed_by_user(self):
        print("clsoed")        
        

class Simulation(object):
    
    def __init__(self, width=600, height=600, p0=(0.0,0.0), p1=(1.0,1.0), background=(0,0,0,0)):
        self.Screen = Screen(width, height, p0, p1, clear_color=background)
        self.FrameRate = 25.0
        self.LastFrame = 0.0
        self.Stop = False
        
    def run(self):
        self.setup(self.Screen)
        while not self.Stop:
            t = time.time()
            t1 = self.LastFrame + 1.0/self.FrameRate
            if t < t1:
                time.sleep(t1 - t)
            self.LastFrame = time.time()
            self.Screen.start_frame()
            self.draw(self.Screen)       
            self.Screen.end_frame()
            
    # overridables 
    def setup(self, screen):
        pass
        
    def draw(self, screen):
        pass

if __name__ == "__main__":
    import time
    D = 500
    N = 100
    
    class MySimulation(Simulation):
        
        def setup(self, _):
            self.Points = [
                np.random.random((2,))*D for _ in range(N)
            ]
            self.LastPoints = None
            _.strokeWeight(5)
            
        def draw(self, _):
            _.clear()
            self.LastPoints = self.Points
            self.Points = self.Points + np.random.normal(size=(len(self.Points), 2))*10
            
            for p, q in zip(self.Points, self.LastPoints):
                x, y = p
                _.stroke(x/D, y/D, 0.9, 1.0)
                _.strokeWeight(5)
                _.point(p)
                _.strokeWeight(2)
                _.line(p, q)
                
    sim = MySimulation(D, D)
    sim.run()
    
