from time import perf_counter
import numpy as np
import pyqtgraph as pg
#from pyqtgraph.Qt import QtWidgets


class ScrollingPlot(pg.GraphicsLayoutWidget):
    def __init__(self, parent=None, show=False, size=None, title=None, **kargs):
        super().__init__(parent, show, size, title, **kargs)
        
        # 3) Plot in chunks, adding one new plot curve for every 100 samples
        self.chunkSize = 100
        # Remove chunks after we have 10
        self.maxChunks = 20
        self.startTime = perf_counter()
        self.p = self.addPlot()
        self.p.setLabel('bottom', 'Time', 's')
        self.p.setXRange(-40, 0)
        #print(type(self.p))

        self.curves = []
        #print(self.curves)
        self.data = np.empty((self.chunkSize+1,2))
        self.ptr = 0
        self.value = 0
        #self.monoRadio = QtWidgets.QRadioButton('mono')
        
        # update plot
        #global timer
        #self.timer = pg.QtCore.QTimer()
        #self.timer.timeout.connect(self.updateSlot)
        #self.timer.start(50)
        #print('timer started')


    def updateSPlot(self):
        if self.ptr == 0:
            self.startTime = perf_counter()
        now = perf_counter()
        for c in self.curves:
            c.setPos(-(now-self.startTime), 0)
    
        i = self.ptr % self.chunkSize
        if i == 0:
            curve = self.p.plot()
            self.curves.append(curve)
            last = self.data[-1]
            if self.ptr == 0:
                last = [0,self.value]
            self.data = np.zeros((self.chunkSize+1,2))        
            self.data[0] = last
            while len(self.curves) > self.maxChunks:
                c = self.curves.pop(0)
                self.p.removeItem(c)
        else:
            curve = self.curves[-1]
        self.data[i+1,0] = now - self.startTime
        self.data[i+1,1] = self.value
        curve.setData(x=self.data[:i+2, 0], y=self.data[:i+2, 1])
        self.ptr += 1

    def setValue(self, value):
        self.value = value
        self.updateSPlot()

    def clearData(self):
        self.curves = []
        self.data = np.zeros((self.chunkSize+1,2))
        self.ptr = 0
        #self.removeItem(self.p) 
        self.p.clear()
        #self.p.setLabel('bottom', 'Time', 's')
        #self.p.setXRange(-40, 0)
  
    
    
    
