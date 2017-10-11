import os
import vtk, qt, ctk, slicer
import EditorLib
from EditorLib.EditOptions import HelpButton
from EditorLib.EditOptions import EditOptions
from EditorLib import EditUtil
from EditorLib import LabelEffect

#
# The Editor Extension itself.
#
# This needs to define the hooks to become an editor effect.
#

#
# EditorEffectTemplateOptions - see LabelEffect, EditOptions and Effect for superclasses
#

class EditorEffectTemplateOptions(EditorLib.LabelEffectOptions):
  """ EditorEffectTemplate-specfic gui
  """

  def __init__(self, parent=0):
    super(EditorEffectTemplateOptions,self).__init__(parent)

    # self.attributes should be tuple of options:
    # 'MouseTool' - grabs the cursor
    # 'Nonmodal' - can be applied while another is active
    # 'Disabled' - not available
    self.attributes = ('MouseTool')
    self.displayName = 'EditorEffectTemplate Effect'

  def __del__(self):
    super(EditorEffectTemplateOptions,self).__del__()

  def create(self):
    super(EditorEffectTemplateOptions,self).create()
    self.apply = qt.QPushButton("Apply", self.frame)
    self.apply.objectName = self.__class__.__name__ + 'Apply'
    self.apply.setToolTip("Apply the extension operation")
    self.frame.layout().addWidget(self.apply)
    self.widgets.append(self.apply)

    HelpButton(self.frame, "This is a sample with no real functionality.")

    self.connections.append( (self.apply, 'clicked()', self.onApply) )

    # Add vertical spacer
    self.frame.layout().addStretch(1)

  def destroy(self):
    super(EditorEffectTemplateOptions,self).destroy()

  # note: this method needs to be implemented exactly as-is
  # in each leaf subclass so that "self" in the observer
  # is of the correct type
  def updateParameterNode(self, caller, event):
    node = EditUtil.EditUtil().getParameterNode()
    if node != self.parameterNode:
      if self.parameterNode:
        node.RemoveObserver(self.parameterNodeTag)
      self.parameterNode = node
      self.parameterNodeTag = node.AddObserver(vtk.vtkCommand.ModifiedEvent, self.updateGUIFromMRML)

  def setMRMLDefaults(self):
    super(EditorEffectTemplateOptions,self).setMRMLDefaults()

  def updateGUIFromMRML(self,caller,event):
    self.disconnectWidgets()
    super(EditorEffectTemplateOptions,self).updateGUIFromMRML(caller,event)
    self.connectWidgets()

  def onApply(self):
    print('This is just an example - nothing here yet')

  def updateMRMLFromGUI(self):
    if self.updatingGUI:
      return
    disableState = self.parameterNode.GetDisableModifiedEvent()
    self.parameterNode.SetDisableModifiedEvent(1)
    super(EditorEffectTemplateOptions,self).updateMRMLFromGUI()
    self.parameterNode.SetDisableModifiedEvent(disableState)
    if not disableState:
      self.parameterNode.InvokePendingModifiedEvent()


#
# EditorEffectTemplateTool
#

class EditorEffectTemplateTool(LabelEffect.LabelEffectTool):
  """
  One instance of this will be created per-view when the effect
  is selected.  It is responsible for implementing feedback and
  label map changes in response to user input.
  This class observes the editor parameter node to configure itself
  and queries the current view for background and label volume
  nodes to operate on.
  """

  def __init__(self, sliceWidget):
    super(EditorEffectTemplateTool,self).__init__(sliceWidget)
    # create a logic instance to do the non-gui work
    self.logic = EditorEffectTemplateLogic(self.sliceWidget.sliceLogic())

  def cleanup(self):
    super(EditorEffectTemplateTool,self).cleanup()

  def processEvent(self, caller=None, event=None):
    """
    handle events from the render window interactor
    """

    # let the superclass deal with the event if it wants to
    if super(EditorEffectTemplateTool,self).processEvent(caller,event):
      return

    if event == "LeftButtonPressEvent":
      xy = self.interactor.GetEventPosition()
      sliceLogic = self.sliceWidget.sliceLogic()
      logic = EditorEffectTemplateLogic(sliceLogic)
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
# EditorEffectTemplateLogic
#

class EditorEffectTemplateLogic(LabelEffect.LabelEffectLogic):
  """
  This class contains helper methods for a given effect
  type.  It can be instanced as needed by an EditorEffectTemplateTool
  or EditorEffectTemplateOptions instance in order to compute intermediate
  results (say, for user feedback) or to implement the final
  segmentation editing operation.  This class is split
  from the EditorEffectTemplateTool so that the operations can be used
  by other code without the need for a view context.
  """

  def __init__(self,sliceLogic):
    self.sliceLogic = sliceLogic
    self.fillMode = 'Plane'

  def apply(self,xy):
    #
    # get the parameters from MRML
    #
    node = EditUtil.EditUtil().getParameterNode()
    tolerance = 50
    maxPixels = 10000
    paintOver = 0
    paintThreshold = 0 
    thresholdMin = 25
    thresholdMax = 25
    
    #tolerance = float(node.GetParameter("WandEffect,tolerance"))
    #maxPixels = float(node.GetParameter("WandEffect,maxPixels"))
    #self.fillMode = node.GetParameter("WandEffect,fillMode")
    #paintOver = int(node.GetParameter("LabelEffect,paintOver"))
    #paintThreshold = int(node.GetParameter("LabelEffect,paintThreshold"))
    #thresholdMin = float(node.GetParameter("LabelEffect,paintThresholdMin"))
    #thresholdMax = float(node.GetParameter("LabelEffect,paintThresholdMax"))

    #
    # get the label and background volume nodes
    #
    labelLogic = self.sliceLogic.GetLabelLayer()
    labelNode = labelLogic.GetVolumeNode()
    backgroundLogic = self.sliceLogic.GetBackgroundLayer()
    backgroundNode = backgroundLogic.GetVolumeNode()

    #
    # get the ijk location of the clicked point
    # by projecting through patient space back into index
    # space of the volume.  Result is sub-pixel, so round it
    # (note: bg and lb will be the same for volumes created
    # by the editor, but can be different if the use selected
    # different bg nodes, but that is not handled here).
    #
    xyToIJK = labelLogic.GetXYToIJKTransform()
    ijkFloat = xyToIJK.TransformDoublePoint(xy+(0,))
    ijk = []
    for element in ijkFloat:
      try:
        intElement = int(round(element))
      except ValueError:
        intElement = 0
      ijk.append(intElement)
    ijk.reverse()
    ijk = tuple(ijk)

    #
    # Get the numpy array for the bg and label
    #
    import vtk.util.numpy_support, numpy
    backgroundImage = backgroundNode.GetImageData()
    labelImage = labelNode.GetImageData()
    shape = list(backgroundImage.GetDimensions())
    shape.reverse()
    backgroundArray = vtk.util.numpy_support.vtk_to_numpy(backgroundImage.GetPointData().GetScalars()).reshape(shape)
    labelArray = vtk.util.numpy_support.vtk_to_numpy(labelImage.GetPointData().GetScalars()).reshape(shape)

    if self.fillMode == 'Plane':
      # select the plane corresponding to current slice orientation
      # for the input volume
      ijkPlane = self.sliceIJKPlane()
      i,j,k = ijk
      if ijkPlane == 'JK':
        backgroundDrawArray = backgroundArray[:,:,k]
        labelDrawArray = labelArray[:,:,k]
        ijk = (i, j)
      if ijkPlane == 'IK':
        backgroundDrawArray = backgroundArray[:,j,:]
        labelDrawArray = labelArray[:,j,:]
        ijk = (i, k)
      if ijkPlane == 'IJ':
        backgroundDrawArray = backgroundArray[i,:,:]
        labelDrawArray = labelArray[i,:,:]
        ijk = (j, k)
    elif self.fillMode == 'Volume':
      backgroundDrawArray = backgroundArray
      labelDrawArray = labelArray

    #
    # do a recursive search for pixels to change
    #
    self.undoRedo.saveState()
    value = backgroundDrawArray[ijk]
    label = EditUtil.EditUtil().getLabel()
    if paintThreshold:
      lo = thresholdMin
      hi = thresholdMax
    else:
      lo = value - tolerance
      hi = value + tolerance
    pixelsSet = 0
    toVisit = [ijk,]
    # Create a map that contains the location of the pixels
    # that have been already visited (added or considered to be added).
    # This is required if paintOver is enabled because then we reconsider
    # all pixels (not just the ones that have not labelled yet).
    if paintOver:
      labelDrawVisitedArray = numpy.zeros(labelDrawArray.shape,dtype='bool')

    while toVisit != []:
      location = toVisit.pop(0)
      try:
        l = labelDrawArray[location]
        b = backgroundDrawArray[location]
      except IndexError:
        continue
      if (not paintOver and l != 0):
        # label filled already and not painting over, leave it alone
        continue
      if (paintOver and l == label):
        # label is the current one, but maybe it was filled with another high/low value,
        # so we have to visit it once (and only once) in this session, too
        if  labelDrawVisitedArray[location]:
          # visited already, so don't try to fill it again
          continue
        else:
          # we'll visit this pixel now, so mark it as visited
          labelDrawVisitedArray[location] = True
      if b < lo or b > hi:
        continue
      labelDrawArray[location] = label
      if l != label:
        # only count those pixels that were changed (to allow step-by-step growing by multiple mouse clicks)
        pixelsSet += 1
      if pixelsSet > maxPixels:
        toVisit = []
      else:
        if self.fillMode == 'Plane':
          # add the 4 neighbors to the stack
          toVisit.append((location[0] - 1, location[1]     ))
          toVisit.append((location[0] + 1, location[1]     ))
          toVisit.append((location[0]    , location[1] - 1 ))
          toVisit.append((location[0]    , location[1] + 1 ))
        elif self.fillMode == 'Volume':
          # add the 6 neighbors to the stack
          toVisit.append((location[0] - 1, location[1]    , location[2]    ))
          toVisit.append((location[0] + 1, location[1]    , location[2]    ))
          toVisit.append((location[0]    , location[1] - 1, location[2]    ))
          toVisit.append((location[0]    , location[1] + 1, location[2]    ))
          toVisit.append((location[0]    , location[1]    , location[2] - 1))
          toVisit.append((location[0]    , location[1]    , location[2] + 1))

    # signal to slicer that the label needs to be updated
    EditUtil.EditUtil().markVolumeNodeAsModified(labelNode)


#
# The EditorEffectTemplate class definition
#

class EditorEffectTemplateExtension(LabelEffect.LabelEffect):
  """Organizes the Options, Tool, and Logic classes into a single instance
  that can be managed by the EditBox
  """

  def __init__(self):
    # name is used to define the name of the icon image resource (e.g. EditorEffectTemplate.png)
    self.name = "EditorEffectTemplate"
    # tool tip is displayed on mouse hover
    self.toolTip = "Paint: circular paint brush for label map editing"

    self.options = EditorEffectTemplateOptions
    self.tool = EditorEffectTemplateTool
    self.logic = EditorEffectTemplateLogic

""" Test:

sw = slicer.app.layoutManager().sliceWidget('Red')
import EditorLib
pet = EditorLib.EditorEffectTemplateTool(sw)

"""

#
# EditorEffectTemplate
#

class EditorEffectTemplate:
  """
  This class is the 'hook' for slicer to detect and recognize the extension
  as a loadable scripted module
  """
  def __init__(self, parent):
    parent.title = "Editor EditorEffectTemplate Effect"
    parent.categories = ["Developer Tools.Editor Extensions"]
    parent.contributors = ["Steve Pieper (Isomics)"] # insert your name in the list
    parent.helpText = """
    Example of an editor extension.  No module interface here, only in the Editor module
    """
    parent.acknowledgementText = """
    This editor extension was developed by
    <Author>, <Institution>
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
    slicer.modules.editorExtensions['EditorEffectTemplate'] = EditorEffectTemplateExtension

#
# EditorEffectTemplateWidget
#

class EditorEffectTemplateWidget:
  def __init__(self, parent = None):
    self.parent = parent

  def setup(self):
    # don't display anything for this widget - it will be hidden anyway
    pass

  def enter(self):
    pass

  def exit(self):
    pass


