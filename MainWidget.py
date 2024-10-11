"""
This example demonstrates the use of pyqtgraph's dock widget system.

The dockarea system allows the design of user interfaces which can be rearranged by
the user at runtime. Docks can be moved, resized, stacked, and torn out of the main
window. This is similar in principle to the docking system built into Qt, but 
offers a more deterministic dock placement API (in Qt it is very difficult to 
programatically generate complex dock arrangements). Additionally, Qt's docks are 
designed to be used as small panels around the outer edge of a window. Pyqtgraph's 
docks were created with the notion that the entire window (or any portion of it) 
would consist of dockable components.
"""

import numpy as np

import pyqtgraph as pg
from pyqtgraph.Qt.QtWidgets import QFileDialog
from pyqtgraph.console import ConsoleWidget
from pyqtgraph.dockarea.Dock import Dock
from pyqtgraph.dockarea.DockArea import DockArea
from pyqtgraph.Qt import QtWidgets
#import pyqtgraph.parametertree.parameterTypes as pTypes
#from pyqtgraph.parametertree import Parameter, ParameterTree
from parametertree import MyParamTree

from CameraView import *
from scrollingPlot import *
#from FileWriter import *

#from PySide6.QtCore import QThread, Signal


class MainWindow(QtWidgets.QMainWindow):
    logSignal = Signal(bool)
    fileNameSignal = Signal(str)

    """ example application main window """
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        area = DockArea()
        self.setCentralWidget(area)
        self.resize(1500,1000)
        self.setWindowTitle('Fischerlab: camera widget')


        ## Create docks, place them into the window one at a time.
        ## Note that size arguments are only a suggestion; docks will still have to
        ## fill the entire dock area and obey the limits of their internal widgets.
        d1 = Dock("main", size=(1, 1))     ## give this dock the minimum possible size
        d2 = Dock("Dock2 - console not used", size=(100,300), closable=True)
        d3 = Dock("settings", size=(100,100))
        d4 = Dock("ROI - peak", size=(1,1))
        d5 = Dock("camera view", size=(500,500))
        d6 = Dock("ROI - sum", size=(500,200))
        #area.addDock(d2, 'right')     ## place d2 at right edge of dock area
        area.addDock(d1, 'left')      ## place d1 at left edge of dock area (it will fill the whole space since there are no other docks yet)
        area.addDock(d3, 'bottom', d1)## place d3 at bottom edge of d1
        area.addDock(d4, 'right')     ## place d4 at right edge of dock area
        area.addDock(d5, 'bottom', d4)  ## place d5 at left edge of d1
        area.addDock(d6, 'top', d4)   ## place d5 at top edge of d4

        ## Test ability to move docks programatically after they have been placed
        #area.moveDock(d4, 'top', d2)     ## move d4 to top edge of d2
        area.moveDock(d6, 'above', d4)   ## move d6 to stack on top of d4
        #area.moveDock(d5, 'top', d2)     ## move d5 to top edge of d2


        ## Add widgets into each dock

        ## first dock gets save/restore buttons
        w1 = pg.LayoutWidget()
        label = QtWidgets.QLabel(""" Main Controls
        """)
        saveBtn = QtWidgets.QPushButton('Start')
        restoreBtn = QtWidgets.QPushButton('Stop')
        clearBtn = QtWidgets.QPushButton('Clear')
        snapshotBtn = QtWidgets.QPushButton('Snapshot')
        addTIBtn = QtWidgets.QPushButton('Add TargetItem')
        deleteTIsBtn = QtWidgets.QPushButton('Delete TargetItems')

        def addSpacer(self, target):
            spacer = QtWidgets.QSpacerItem(1,20)
            target.layout.addItem(spacer)




        #restoreBtn.setEnabled(False)
        w1.addWidget(label, row=0, col=0)
        w1.addWidget(saveBtn, row=1, col=0)
        w1.addWidget(restoreBtn, row=2, col=0)
        w1.addWidget(clearBtn, row=3, col=0)
        addSpacer(self, w1)
        w1.addWidget(snapshotBtn, row=5, col=0)
        addSpacer(self, w1)
        w1.addWidget(addTIBtn, row=7, col=0)
        w1.addWidget(deleteTIsBtn, row=8, col=0)
        d1.addWidget(w1)
        state = None
        def save():
            global state
            state = area.saveState()
            restoreBtn.setEnabled(True)
        def load():
            global state
            area.restoreState(state)
        def CancelFeed():
            self.CameraWorker.stop()
        def StartFeed():
            self.CameraWorker.start()
        #def addTargetItem():
        #    targetItem = pg.TargetItem(pos=(0, 0), label = "test")
        #    self.w5.p1.addItem(targetItem)
        #    self.deleteTIsBtn.clicked.connect(targetItem.deleteLater)

 
        saveBtn.clicked.connect(StartFeed)
        restoreBtn.clicked.connect(CancelFeed)


        w2 = ConsoleWidget()
        d2.addWidget(w2)

        ## Hide title bar on dock 3
        d3.hideTitleBar()
        #w3 = pg.PlotWidget(title="Plot inside dock with no title bar")
        #w3.plot(np.random.normal(size=100))
        self.w3 = MyParamTree()
        d3.addWidget(self.w3)

        #w4 = pg.PlotWidget(title="Dock 4 plot")
        #w4.plot(np.random.normal(size=100))
        self.w4 = ScrollingPlot()
        d4.addWidget(self.w4)



        self.w5 = CameraView() 

        #self.w5.autoLevels()
        d5.addWidget(self.w5)
        addTIBtn.clicked.connect(self.w5.addTargetItem)
        deleteTIsBtn.clicked.connect(self.w5.deleteTIs)



        self.CameraWorker = CameraGrabThread(self)
        self.CameraWorker.ImageUpdate.connect(self.w5.SendImagaRoiDataSlot)
        self.w5.ImageMod.ReadyForImageSignal.connect(self.CameraWorker.setReceiverReady)
        #self.CameraWorker.start()
        self.w3.camParamsChangedSignal.connect(self.CameraWorker.setCamParams)
        self.w3.saveBgSignal.connect(self.w5.ImageMod.saveBgSlot) 
        self.w3.subtBgSignal.connect(self.w5.ImageMod.subtBgSlot)
        self.w3.forceGSSignal.connect(self.w5.ImageMod.forceGSSlot)
        self.w3.zScaleSignal.connect(self.w5.setzScale)
        self.w3.binFactorSignal.connect(self.w5.ImageMod.binFactorSlot)
        snapshotBtn.clicked.connect(self.w5.ImageMod.snapshotSlot) 

        '''self.w3.logSignal.connect() Proper connection slot needs to be figured out'''

  
        self.w6 = ScrollingPlot()#pg.PlotWidget(title="Dock 6 plot")
        d6.addWidget(self.w6)


        self.w5.ImageMod.roiMaxUpdate.connect(self.w4.setValue)
        self.w5.ImageMod.roiIntUpdate.connect(self.w6.setValue)
        clearBtn.clicked.connect(self.w4.clearData)
        clearBtn.clicked.connect(self.w6.clearData)


        if len(self.CameraWorker.camdict) > 0:
            camBranch = dict(name='device', type='list', limits=self.CameraWorker.camdict)
            self.w3.camModel.addChild(camBranch)
            model0 = sorted(self.CameraWorker.camdict.keys())
            serial0 = self.CameraWorker.camdict[model0[0]]
            self.CameraWorker.setSerialNumber(serial0)
        self.w3.camChangedSignal.connect(self.ChangeCamSlot)

        self.w3.logSignal.connect(self.logSignalSlot)
        self.logSignal.connect(self.w5.ImageMod.logSignalSlot)
        self.fileNameSignal.connect(self.w5.ImageMod.fileNameSlot)




        '''place where it runs once per checkbox click
        run once with empty string'''

    #@Slot()
    def ChangeCamSlot(self, CamSerial):
        self.CameraWorker.stop()
        self.CameraWorker.wait()
        self.CameraWorker.setSerialNumber(CamSerial)
        self.CameraWorker.start()

    def logSignalSlot(self, logSignal):
        if logSignal:
            file_name, suffix = QFileDialog.getSaveFileName(None, ("Save File"),("./"),("Log Files (*.log)"))
            if not file_name.endswith(".log") and file_name != '': file_name += ".log"
            #print(file_name)
            self.fileNameSignal.emit(file_name)
        self.logSignal.emit(logSignal)


 



        



    def closeEvent(self, event):
        self.CameraWorker.stop()
        self.w5.imodthread.quit()
        self.CameraWorker.wait()
        self.w5.imodthread.wait()
        event.accept()




if __name__ == '__main__':
    app = pg.mkQApp("DockArea Example")
    widget = MainWindow()
    widget.show() 
    pg.exec()




