from typing import Optional
import pyqtgraph as pg
import numpy as np
from pyqtgraph.Qt.QtWidgets import QFileDialog
import pyqtgraph as pg
from pyqtgraph.console import ConsoleWidget
from pyqtgraph.dockarea.Dock import Dock
from pyqtgraph.dockarea.DockArea import DockArea
from pyqtgraph.Qt import QtWidgets
from pyqtgraph.Qt.QtCore import QThread, QObject, Signal
from pypylon import pylon
from time import perf_counter
import cv2
import time

color = 1


class CameraView(pg.GraphicsLayoutWidget):
    ImageDataUpdate = Signal(pg.ROI,np.ndarray)
    deleteTIs = Signal()
 
    def __init__(self, parent=None, show=False, size=None, title=None, **kargs):
        super().__init__(parent, show, size, title, **kargs)
        self.p1 = self.addPlot(title="")
        self.p1.setAspectLocked(True,1)



        # initialize some variables
        self.zScaleMode = 0
        self.data = np.zeros(shape=(3860, 2178))


        # Item for displaying image data
        self.img = pg.ImageItem()
        self.img.setImage(self.data)
        self.p1.addItem(self.img)

        # Custom ROI for selecting an image region
        self.roi = pg.RectROI([1500, 1000], [500, 250])
        self.roi.addScaleHandle([0.5, 1], [0.5, 0.5])
        self.roi.addScaleHandle([0, 0.5], [0.5, 0.5])
        self.p1.addItem(self.roi)
        self.roi.setZValue(100)  # make sure ROI is drawn above image

        #self.roi.sigRegionChanged.connect(self.RoiChanged)

        # Contrast/color control
        self.hist = pg.HistogramLUTItem()
        self.hist.gradient.loadPreset('turbo')
        self.hist.setImageItem(self.img)
        self.addItem(self.hist)

        #move stuff to thread to avoid freezing

        self.ImageMod = ImageModThread(parent=self)
        self.imodthread = QThread()
        self.ImageMod.moveToThread(self.imodthread)
        self.imodthread.start()
        self.ImageMod.ImageReadySignal.connect(self.ImageUpdateSlot)
        self.ImageDataUpdate.connect(self.ImageMod.ImageModSlot)
        #self.updater.roiDataUpdateSignal.connect(self.SendRoiDataSlot)

        def imageHoverEvent(event):
            """Show the position, pixel, and value under the mouse cursor.
            """
            if event.isExit():
                self.p1.setTitle("")
                return
            pos = event.pos()
            i, j = pos.x(), pos.y()
            i = int(np.clip(i, 0, self.data.shape[0] - 1))
            j = int(np.clip(j, 0, self.data.shape[1] - 1))
            val = self.data[i, j]
            ppos = self.img.mapToParent(pos)
            x, y = ppos.x(), ppos.y()
            self.p1.setTitle("pixel: (%d, %d)  value: %.3g" % (i, j, val))

        # Monkey-patch the image to use our custom hover function. 
        # This is generally discouraged (you should subclass ImageItem instead),
        # but it works for a very simple use like this. 
        self.img.hoverEvent = imageHoverEvent

    def ImageUpdateSlot(self, image, roimax):
        if self.zScaleMode == 0: self.img.setImage(image, autoLevels = True)
        elif self.zScaleMode == 1: self.img.setImage(image, levels = [0, roimax])
        elif self.zScaleMode == 2: self.img.setImage(image, autoLevels = False)
        #x = self.p1.getViewBox().viewRange()

    def SendImagaRoiDataSlot(self, image):
        self.ImageDataUpdate.emit(self.roi, image)

    def setzScale(self, zscalemode):
        self.zScaleMode = zscalemode
        #if zscalemode == 0: self.img.setLevels([0, 255], update = True)

 
    def addTargetItem(self):
        def callableFunction(x, y):
            return f"({x:.0f}, {y:.0f})"
        targetItem = CustomTargetItem(parent = self, pos=(0, 0), label = callableFunction)
        self.p1.addItem(targetItem)
        #self.p1.removeItem(targetItem)
        #targetItem.deleteLater() 
        self.deleteTIs.connect(targetItem.deleteItem)

 

class CustomTargetItem(pg.TargetItem):
    def __init__(self, parent=None, pos=None, size=10, symbol='crosshair', pen=None, hoverPen=None, brush=None, hoverBrush=None, movable=True, label=None, labelOpts=None):
        global color
        super().__init__(pos, size, symbol, color, hoverPen, brush, hoverBrush, movable, label, labelOpts)
            #pos=pos, size=size, symbol=symbol, pen=pen, hoverPen=hoverPen, brush=brush, hoverBrush=hoverBrush, movable=movable, label=label, labelOpts=labelOpts)
        self.parent=parent
        color += 1
    def deleteItem(self):
        global color
        if self.parent:
            color -= 1 
            self.parent.p1.removeItem(self)
            self.deleteLater()



class ImageModThread(QObject):
    ImageReadySignal = Signal(np.ndarray, int)
    ReadyForImageSignal = Signal()
    roiIntUpdate = Signal(int)
    roiMaxUpdate = Signal(int)
    def __init__(self, *args, **kwargs):
        super(ImageModThread,self).__init__()
        self.bg = np.zeros(shape=(3860, 2178))
        self.data = np.zeros(shape=(3860, 2178))
        self.takeSnapshot = False
        self.saveBg = False
        self.subtBg = False
        self.bgexists = False
        self.binFactor = 1
        self.fileName = None
        self.logSignal = False
        self.forceGS = False
        self.f = None
        #self.fileStatus = "closed"
        self.logStartTime = perf_counter()

    def ImageModSlot(self, roi, image):
        #First, do background subtraction
        self.data = image
        if self.saveBg:
            self.saveBg = False
            self.bgexists = True
            self.bg = image
        if self.subtBg and self.bgexists: self.data = (image > self.bg) * np.subtract(image,self.bg)  # + (Image<self.bg)*np.subtract(self.bg, Image)
        if self.forceGS and len(self.data.shape) == 3: self.data = cv2.cvtColor(self.data, cv2.COLOR_BGR2GRAY) 
        if self.binFactor > 1:
            if len(self.data.shape) == 2: self.data = self.rebin(self.data, self.binFactor)
            elif len(self.data.shape) == 3: 
                self.data = cv2.resize(self.data, (0,0), fx = 1/self.binFactor, fy = 1/self.binFactor)

        #Second, analyze roi int and max
        dim = np.shape(self.data)
        xmin = np.clip(int(roi.pos().x()),0,dim[0]) #pos returns lower left corner
        ymin = np.clip(int(roi.pos().y()),0,dim[1])
        xmax = np.clip(int(roi.pos().x() + roi.size().x()),0,dim[0])
        ymax = np.clip(int(roi.pos().y() + roi.size().y()),0,dim[1])        
        #crop by hand
        if len(self.data.shape) == 2: roiArray = self.data[xmin:xmax, ymin:ymax]
        if len(self.data.shape) == 3:
            gray_image = cv2.cvtColor(self.data, cv2.COLOR_BGR2GRAY)
            roiArray = gray_image[xmin:xmax, ymin:ymax]
        if np.shape(roiArray)[0] > 0 and  np.shape(roiArray)[1] > 0:
            roiint = np.sum(roiArray)
            roimax = np.max(roiArray)
        else:
            roiint = 0
            roimax = 0

        #Between analysis and signals, log results to file of user's choice if active
        if self.logSignal and self.fileName != "":
            if not self.f or self.f.closed:
                self.f = open(self.fileName, 'a')
                self.logStartTime = perf_counter()
                print(self.fileName + " opened")
            roiintstr = str(roiint)
            roimaxstr = str(roimax)
            logTotalTime = perf_counter()
            logWriteTime = logTotalTime - self.logStartTime
            logWriteTime = str(logWriteTime)
            self.f.write(logWriteTime + " " + roiintstr + " " + roimaxstr + "\n")
        if not self.logSignal and self.f and not self.f.closed:
            #if self.f and not self.f.closed:
            self.f.close()
            print(self.fileName + " closed")
            self.f = None

        if self.takeSnapshot:
            self.takeSnapshot = False
            filename = "./snapshot_" + time.strftime("%Y%m%d-%H%M%S") + ".png"
            cv2.imwrite(filename, cv2.rotate(self.data, cv2.ROTATE_90_COUNTERCLOCKWISE))
            print(filename + " saved")

        #Third, send signals
        self.ImageReadySignal.emit(self.data, roimax) #connected to cameraview
        self.roiIntUpdate.emit(roiint) #connected to scrolling plot
        self.roiMaxUpdate.emit(roimax) #connected to scrolling plot
        self.ReadyForImageSignal.emit() #connected to camera worker

    def rebin(self, image, binFactor):
        """
        `a` is the N-dim input array
        `factors` is the blocksize on which averaging is to be performed
        """
        lenx, leny = image.shape
        binx = binFactor
        biny = binFactor
        factors = [binx, biny]
        image = image[:binx * int(lenx / binx), :biny * int(leny / biny)]
        factors = np.asanyarray(factors)
        sh = np.column_stack([image.shape // factors, factors]).ravel()
        b = image.reshape(sh).mean(tuple(range(1, 2 * image.ndim, 2)))
        return b


    def snapshotSlot(self):
        self.takeSnapshot = True
    def saveBgSlot(self):
        self.saveBg = True
    def subtBgSlot(self, subtBg):
        self.subtBg = subtBg
    def forceGSSlot(self, forceGS):
        self.forceGS = forceGS
    def binFactorSlot(self, binFactor):
        self.binFactor = binFactor
    def logSignalSlot(self, logSignal):
        self.logSignal = logSignal
        #if self.filename == "": self.logSignal = False
    def fileNameSlot(self, fileNameSignal):
        self.fileName = fileNameSignal




class CameraGrabThread(QThread, QObject):  
    ImageUpdate = Signal(np.ndarray)
    expAuto = True
    expTime = 0
    gainAuto = True
    gain = 0.0
    SerialNumber = '0'
    def __init__(self, parent: QObject | None = ...) -> None:
        super().__init__(parent)
        tlFactory = pylon.TlFactory.GetInstance()
        # Get all attached devices and exit application if no device is found.
        devices = tlFactory.EnumerateDevices()
        if len(devices) == 0:
            raise pylon.RuntimeException("No camera present.")

        # Create an array of instant cameras for the found devices and avoid exceeding a maximum number of devices.
        cameras = pylon.InstantCameraArray(min(len(devices), 4))

        l = cameras.GetSize()
        self.camdict = {}
        for i, cam in enumerate(cameras):
            cam.Attach(tlFactory.CreateDevice(devices[i]))
            self.camdict[cam.GetDeviceInfo().GetModelName()] = cam.GetDeviceInfo().GetSerialNumber()
            #self.camdict['test']=1#test


    def run(self):
        self.ThreadActive = True
        self.setCamPams_b = False
        self.receiverReady = True

        devInfo = pylon.DeviceInfo()
        devInfo.SetSerialNumber(self.SerialNumber)
        
        camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice(devInfo))
        camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
        converter = pylon.ImageFormatConverter()
        # converting to opencv bgr format
        converter.OutputPixelFormat = pylon.PixelType_BGR8packed
        converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned
        #Capture = cv2.VideoCapture(0)
        i=0
        while self.ThreadActive and camera.IsGrabbing():
            #camera.IsGrabbing()
            #QCoreApplication.processEvents()
            #i+=1
            grabResult = camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
            #print("grab %d" % i)
            if grabResult.GrabSucceeded():
                image2 = converter.Convert(grabResult)
                img = image2.GetArray()
                #img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                #Image = cv2.flip(Image, 1)
                img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB) 
                #blue_channel = img[:,:,0]             
                #green_channel = img[:,:,1]             
                #red_channel = img[:,:,2]   
                Image = img#0*blue_channel + 0*green_channel + red_channel
                #resized = cv2.resize(img, (100,100), interpolation = cv2.INTER_AREA)
                #array = np.asarray(img)
                #Pic = QImage(FlippedImage.data, FlippedImage.shape[1], FlippedImage.shape[0], QImage.Format_RGB888)
                #Pic = ConvertToQtFormat.scaled(3840, 2160, Qt.KeepAspectRatio)
                #print(self.receiverReady)
                if self.receiverReady:
                    self.ImageUpdate.emit(Image)
                    self.receiverReady = False
                    i = 0
                    #print("send %d" % i)
                else:
                    i += 1
                    if i > 10: self.receiverReady = True
                if self.setCamPams_b:
                    self.setCamPams_b = False
                    #print(camera.AutoFunctionProfile.GetValue())
                    if self.expAuto and self.gainAuto:
                        camera.AutoFunctionProfile.SetValue('MinimizeExposureTime')                    
                    if self.expAuto:
                        camera.ExposureAuto.SetValue('Continuous')
                    else:
                        camera.ExposureAuto.SetValue('Off')
                        camera.ExposureTime.SetValue(self.expTime)
                    if self.gainAuto:
                        camera.GainAuto.SetValue('Continuous')
                    else:
                        camera.GainAuto.SetValue('Off')
                        camera.Gain.SetValue(self.gain)
            grabResult.Release()
        camera.StopGrabbing()
    def stop(self):
        self.ThreadActive = False
        self.quit()
    def setReceiverReady(self):
        self.receiverReady = True
    def setSerialNumber(self, SerialNumber):
        self.SerialNumber = SerialNumber

    #@Slot()
    def setCamParams(self, expAuto, expTime, gainAuto, gain):
        self.expAuto = expAuto
        self.expTime = expTime
        self.gainAuto = gainAuto
        self.gain = gain
        #print(gain)
        self.setCamPams_b = True
