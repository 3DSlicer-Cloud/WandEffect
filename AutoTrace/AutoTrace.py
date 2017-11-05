import os
import vtk, qt, ctk, slicer
import EditorLib
from EditorLib.EditOptions import HelpButton
from EditorLib.EditOptions import EditOptions
from EditorLib import EditUtil
from EditorLib import LabelEffect
import TraceAndSelect

#
# The Editor Extension itself.
#
# This needs to define the hooks to become an editor effect.
#

#
# AutoTraceOptions - see LabelEffect, EditOptions and Effect for superclasses
#

class AutoTraceOptions(EditorLib.LabelEffectOptions):
  """ AutoTrace-specfic gui
  """

  def __init__(self, parent=0):
    super(AutoTraceOptions,self).__init__(parent)

    # self.attributes should be tuple of options:
    # 'MouseTool' - grabs the cursor
    # 'Nonmodal' - can be applied while another is active
    # 'Disabled' - not available
    self.attributes = ('MouseTool')
    self.displayName = 'AutoTrace Effect'

  def __del__(self):
    super(AutoTraceOptions,self).__del__()

  def create(self):
    super(AutoTraceOptions,self).create()

    self.maxPixelsFrame = qt.QFrame(self.frame)
    self.maxPixelsFrame.setLayout(qt.QHBoxLayout())
    self.frame.layout().addWidget(self.maxPixelsFrame)
    self.widgets.append(self.maxPixelsFrame)
    self.maxPixelsLabel = qt.QLabel("Max Pixels per click:", self.maxPixelsFrame)
    self.maxPixelsLabel.setToolTip("Set the maxPixels for each click")
    self.maxPixelsFrame.layout().addWidget(self.maxPixelsLabel)
    self.widgets.append(self.maxPixelsLabel)
    self.maxPixelsSpinBox = qt.QDoubleSpinBox(self.maxPixelsFrame)
    self.maxPixelsSpinBox.setToolTip("Set the maxPixels for each click")
    self.maxPixelsSpinBox.minimum = 1
    self.maxPixelsSpinBox.maximum = 100000
    self.maxPixelsSpinBox.suffix = ""
    self.maxPixelsFrame.layout().addWidget(self.maxPixelsSpinBox)
    self.widgets.append(self.maxPixelsSpinBox)

    HelpButton(self.frame, "Use this tool to help you label all voxels enclosed in an area bounded by the the largest path of pixels within the specified threshold.")

    # don't connect the signals and slots directly - instead, add these
    # to the list of connections so that gui callbacks can be cleanly 
    # disabled while the gui is being updated.  This allows several gui
    # elements to be interlinked with signal/slots but still get updated
    # as a unit to the new value of the mrml node.
    self.thresholdPaint.hide()
    self.paintOver.hide()
    self.connections.append( 
        (self.maxPixelsSpinBox, 'valueChanged(double)', self.onMaxPixelsSpinBoxChanged) )
    

    # Add vertical spacer
    self.frame.layout().addStretch(1)

  def destroy(self):
    super(AutoTraceOptions,self).destroy()

  # note: this method needs to be implemented exactly as-is
  # in each leaf subclass so that "self" in the observer
  # is of the correct type 
  def updateParameterNode(self, caller, event):
    node = EditUtil.EditUtil().getParameterNode()
    if node != self.parameterNode:
      if self.parameterNode:
        node.RemoveObserver(self.parameterNodeTag)
      self.parameterNode = node
      self.parameterNodeTag = node.AddObserver("ModifiedEvent", self.updateGUIFromMRML)

  def setMRMLDefaults(self):
    #super(AutoTraceOptions,self).setMRMLDefaults()
    disableState = self.parameterNode.GetDisableModifiedEvent()
    self.parameterNode.SetDisableModifiedEvent(1)
    defaults = (
      ("maxPixels", "2500"),
    )
    for d in defaults:
      param = "AutoTrace,"+d[0]
      pvalue = self.parameterNode.GetParameter(param)
      if pvalue == '':
        self.parameterNode.SetParameter(param, d[1])
    defaults = (
      ("paintOver", "1"),
      ("paintThreshold", "1"),
      ("paintThresholdMin", "250"),
      ("paintThresholdMax", "2799"),
    )
    for d in defaults:
      param = "LabelEffect,"+d[0]
      pvalue = self.parameterNode.GetParameter(param)
      if pvalue == '':
        self.parameterNode.SetParameter(param, d[1])
    self.parameterNode.SetDisableModifiedEvent(disableState)

  def updateGUIFromMRML(self,caller,event):
    params = ("maxPixels",)
    for p in params:
      if self.parameterNode.GetParameter("AutoTrace,"+p) == '':
        # don't update if the parameter node has not got all values yet
        return
    super(AutoTraceOptions,self).updateGUIFromMRML(caller,event)
    self.disconnectWidgets()
    self.maxPixelsSpinBox.setValue( float(self.parameterNode.GetParameter("AutoTrace,maxPixels")) )
    self.connectWidgets()

  def onToleranceSpinBoxChanged(self,value):
    if self.updatingGUI:
      return
    self.updateMRMLFromGUI()

  def onMaxPixelsSpinBoxChanged(self,value):
    if self.updatingGUI:
      return
    self.updateMRMLFromGUI()

  def updateMRMLFromGUI(self):
    disableState = self.parameterNode.GetDisableModifiedEvent()
    self.parameterNode.SetDisableModifiedEvent(1)
    super(AutoTraceOptions,self).updateMRMLFromGUI()
    self.parameterNode.SetParameter( "AutoTrace,maxPixels", str(self.maxPixelsSpinBox.value) )
    self.parameterNode.SetDisableModifiedEvent(disableState)
    if not disableState:
      self.parameterNode.InvokePendingModifiedEvent()


#
# AutoTraceTool
#

class AutoTraceTool(LabelEffect.LabelEffectTool):
  """
  One instance of this will be created per-view when the effect
  is selected.  It is responsible for implementing feedback and
  label map changes in response to user input.
  This class observes the editor parameter node to configure itself
  and queries the current view for background and label volume
  nodes to operate on.
  """

  def __init__(self, sliceWidget):
    super(AutoTraceTool,self).__init__(sliceWidget)
    # create a logic instance to do the non-gui work
    self.logic = AutoTraceLogic(self.sliceWidget.sliceLogic())

  def cleanup(self):
    super(AutoTraceTool,self).cleanup()

  def processEvent(self, caller=None, event=None):
    """
    handle events from the render window interactor
    """

    # let the superclass deal with the event if it wants to
    if super(AutoTraceTool,self).processEvent(caller,event):
      return

    if event == "LeftButtonPressEvent":
      xy = self.interactor.GetEventPosition()
      sliceLogic = self.sliceWidget.sliceLogic()
      logic = AutoTraceLogic(sliceLogic)
      logic.undoRedo = self.undoRedo
      logic.apply(xy)
      print("Got a %s at %s in %s" % (event,str(xy),self.sliceWidget.sliceLogic().GetSliceNode().GetName()))
      self.abortEvent(event)
    else:
      pass

    # events from the slice node
    if caller and caller.IsA('vtkMRMLSliceNode'):
      # here you can respond to pan/zoom or other changes
      # to the view
      pass


#
# AutoTraceLogic
#

class AutoTraceLogic(TraceAndSelect.TraceAndSelectLogic):
  """
  This class contains helper methods for a given effect
  type.  It can be instanced as needed by an AutoTraceTool
  or AutoTraceOptions instance in order to compute intermediate
  results (say, for user feedback) or to implement the final
  segmentation editing operation.  This class is split
  from the AutoTraceTool so that the operations can be used
  by other code without the need for a view context.
  """

  def __init__(self,sliceLogic):
    self.sliceLogic = sliceLogic
    self.fillMode = 'Plane'

  def apply(self,xy):
    TraceAndSelectLogic.apply(self,xy)

#
# The AutoTrace class definition
#

class AutoTraceExtension(LabelEffect.LabelEffect):
  """Organizes the Options, Tool, and Logic classes into a single instance
  that can be managed by the EditBox
  """

  def __init__(self):
    # name is used to define the name of the icon image resource (e.g. AutoTrace.png)
    self.name = "AutoTrace"
    # tool tip is displayed on mouse hover
    self.toolTip = "Paint: circular paint brush for label map editing"

    self.options = AutoTraceOptions
    self.tool = AutoTraceTool
    self.logic = AutoTraceLogic

""" Test:

sw = slicer.app.layoutManager().sliceWidget('Red')
import EditorLib
pet = EditorLib.AutoTraceTool(sw)

"""

#
# AutoTrace
#

class AutoTrace:
  """
  This class is the 'hook' for slicer to detect and recognize the extension
  as a loadable scripted module
  """
  def __init__(self, parent):
    parent.title = "Editor AutoTrace Effect"
    parent.categories = ["Developer Tools.Editor Extensions"]
    parent.contributors = ["Steven Friedland, Peter Shultz, Nathan Gieseker, Matthew Holbrook"] # insert your name in the list
    parent.helpText = """
    Example of an editor extension.  No module interface here, only in the Editor module
    """
    parent.acknowledgementText = """
    This editor extension was developed by
    stfried, pshultz, gieseker, mthol
    based on work by:
    Steve Pieper, Isomics, Inc.
    based on work by:
    Jean-Christophe Fillion-Robin, Kitware Inc.
    and was partially funded by NIH grant 3P41RR013218.
    """

    # TODO:
    # don't show this module - it only appears in the Editor module
    #parent.hidden = True

    # Add this extension to the editor's list for discovery when the module
    # is created.  Since this module may be discovered before the Editor itself,
    # create the list if it doesn't already exist.
    try:
      slicer.modules.editorExtensions
    except AttributeError:
      slicer.modules.editorExtensions = {}
    slicer.modules.editorExtensions['AutoTrace'] = AutoTraceExtension

#
# AutoTraceWidget
#

class AutoTraceWidget:
  def __init__(self, parent = None):
    self.parent = parent

  def setup(self):
    # don't display anything for this widget - it will be hidden anyway
    pass

  def enter(self):
    pass

  def exit(self):
    pass

# Steven wuz here