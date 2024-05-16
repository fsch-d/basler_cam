import pyqtgraph as pg
from pyqtgraph.Qt import QtCore
from pyqtgraph.Qt.QtCore import Signal, Slot
#import pyqtgraph.parametertree.parameterTypes as pTypes
from pyqtgraph.parametertree import Parameter, ParameterTree




class MyParamTree(ParameterTree):
    camParamsChangedSignal = Signal(bool, int, bool, float)
    camChangedSignal = Signal(str)
    saveBgSignal = Signal()
    subtBgSignal = Signal(bool)
    forceGSSignal = Signal(bool)
    zScaleSignal = Signal(int)
    binFactorSignal = Signal(int)
    logSignal = Signal(bool)
    
    expMode = False
    expTime = 25000
    gainMode = False
    gain = 0




    camParam = [
                {'name': 'auto exposure', 'type': 'bool', 'value': expMode},
                {'name': 'exposure time', 'type': 'int', 'suffix': ' mus', 'value': expTime,'limits':[27,999999]},
                {'name': 'auto gain', 'type': 'bool', 'value': gainMode},
                {'name': 'gain', 'type': 'float', 'suffix': ' dB', 'value': gain, 'step': 0.1,'limits':[0,48]}
        ]

    noncamParam = [{'name': 'save background', 'type': 'action'},
                {'name': 'subtract background', 'type': 'bool', 'value': False},                   
                {'name': 'z-scale', 'type': 'list',  'values': {"global": 0, "ROI": 1, "manual": 2}, 'value': 0},
                {'name':'bin-factor', 'type': 'int', 'value':'1'},
                {'name': 'force grayscale', 'type': 'bool', 'value': False},
                {'name':'log-to-file', 'type':'bool', 'value':False},
                #{'name': 'Layer','expanded':False, 'type': 'group','autoIncrementName':True, 'children': [
                #{'name': 'LayerType', 'type': 'list', 'values': {"RGB": 0, "LAB": 1, "ChannelWise": 2}, 'value': 0},
                #{'name': 'Channel', 'type': 'int', 'value': 0,'limits':[0,2]},
                #{'name': 'Opacity', 'type': 'float', 'value': 0.0, 'step': 0.1,'limits':[0,1]},
                #{'name': 'Show', 'type': 'bool', 'value': True, 'tip': "Show / Hide this layer"},
                #{'name': 'HideOthers', 'type': 'action','tip':"Hide all other layers"},
                #{'name': 'Gradient', 'type': 'colormap'},
                #{'name': 'Subgroup', 'type': 'group', 'children': [
                #    {'name': 'Sub-param 1', 'type': 'int', 'value': 10},
                #    {'name': 'Sub-param 2', 'type': 'float', 'value': 1.2e6},
                #]},
                #{'name': 'Text Parameter', 'type': 'text', 'value': 'Some text...'},
                #{'name': 'Action Parameter', 'type': 'action'},
            #]}
            ]

    softParamSpec = [
            dict(name='float', type='float'),
            dict(name='int', type='int'),
            dict(name='str', type='str'),
            dict(name='list', type='list', values=['x','y','z']),
            dict(name='dict', type='list', values={'x':1, 'y':3, 'z':7}),
            dict(name='bool', type='bool'),
        ]
    



    camModel = Parameter.create(name="camera model", type="group")#, children=[{}])
    camParams = Parameter.create(name="camera settings", type="group", children=camParam)
    softParams = Parameter.create(name="general settings", type="group", children=noncamParam)


    @Slot()
    def change(self, param, changes):
        #print("tree changes:")
        for param, _, data in changes:
            path = self.host.childPath(param)
            childName = param.name()
            if path[0] == 'camera settings':
                if childName == 'auto exposure':
                    self.expMode = data
                elif childName == 'exposure time':
                    self.expTime = data
                elif childName == 'auto gain':
                    self.gainMode = data
                elif childName == 'gain':
                    self.gain = data
                self.camParamsChangedSignal.emit(self.expMode, self.expTime, self.gainMode, self.gain)
            elif path[0] == 'general settings':
                if childName == 'save background': self.saveBgSignal.emit()
                elif childName == 'subtract background': self.subtBgSignal.emit(data)
                elif childName == 'force grayscale': self.forceGSSignal.emit(data)
                elif childName == 'z-scale': self.zScaleSignal.emit(data)
                elif childName == 'bin-factor': self.binFactorSignal.emit(data)
                elif childName == 'log-to-file':self.logSignal.emit(data)
            if path[0] == 'camera model':
                self.camChangedSignal.emit(data)
                #print(data)

            #if path is not None:
            #    childName = '.'.join(path)
            #else:
            #print('  parameter: %s'% childName)
            #print('  change:    %s'% change)
            #print('  data:      %s'% str(data))
            #print('  ----------')
    



    def __init__(self, parent=None, showHeader=True):
        super().__init__(parent, showHeader)
        self.host = Parameter.create(name="Settings", type="group")
        self.host.addChild(self.camModel)
        self.host.addChild(self.camParams)
        self.host.addChild(self.softParams)
        self.setParameters(self.host)
        self.host.sigTreeStateChanged.connect(self.change)



