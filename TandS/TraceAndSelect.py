import os
import vtk, qt, ctk, slicer
import EditorLib
from EditorLib.EditOptions import HelpButton
from EditorLib.EditOptions import EditOptions
from EditorLib import EditUtil
from EditorLib import LabelEffect
import math

#
# The Editor Extension itself.
#
# This needs to define the hooks to become an editor effect.
#

#
# TraceAndSelectOptions - see LabelEffect, EditOptions and Effect for superclasses
#

class TraceAndSelectOptions(EditorLib.LabelEffectOptions):
  """ TraceAndSelect-specfic gui
  """

  def __init__(self, parent=0):
    super(TraceAndSelectOptions,self).__init__(parent)

    # self.attributes should be tuple of options:
    # 'MouseTool' - grabs the cursor
    # 'Nonmodal' - can be applied while another is active
    # 'Disabled' - not available
    self.attributes = ('MouseTool')
    self.displayName = 'TraceAndSelect Effect'
    self.offset = 0
  def __del__(self):
    super(TraceAndSelectOptions,self).__del__()

  def create(self):
    super(TraceAndSelectOptions,self).create()
    
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

    ## For the offset value selection process
    self.offsetvalueFrame = qt.QFrame(self.frame)
    self.offsetvalueFrame.setLayout(qt.QHBoxLayout())
    self.frame.layout().addWidget(self.offsetvalueFrame)
    self.widgets.append(self.offsetvalueFrame)
    self.offsetvalueLabel = qt.QLabel("Offset Value:", self.offsetvalueFrame)
    self.offsetvalueLabel.setToolTip("Set the offset value shift upon an action")
    self.offsetvalueFrame.layout().addWidget(self.offsetvalueLabel)
    self.widgets.append(self.offsetvalueLabel)
    self.offsetvalueSpinBox = qt.QDoubleSpinBox(self.offsetvalueFrame)
    self.offsetvalueSpinBox.setToolTip("Set the offset value shift upon an action")
    self.offsetvalueSpinBox.minimum = -1000
    self.offsetvalueSpinBox.maximum = 1000
    self.offsetvalueSpinBox.suffix = ""
    self.offsetvalueFrame.layout().addWidget(self.offsetvalueSpinBox)
    self.widgets.append(self.offsetvalueSpinBox)
    ## End offset value selection
 
    ## ERROR MESSAGE FRAME
    self.errorMessageFrame = qt.QTextEdit(self.frame)
    self.frame.layout().addWidget(self.errorMessageFrame)
    #self.errorMessageFrame.setLayout(qt.QHBoxLayout)
    self.errorMessageFrame.setFixedWidth(280)
    self.errorMessageFrame.setReadOnly(True)
    self.errorMessageFrame.setText('No Error Detected')
    self.errorMessageFrame.setStyleSheet("QTextEdit {color:green}")
    self.widgets.append(self.errorMessageFrame)
    ## END ERROR MESSAGE FRAME
    
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
    self.connections.append( 
      (self.offsetvalueSpinBox, 'valueChanged(double)', self.onOffsetValueSpinBoxChanged) )


    # Add vertical spacer
    self.frame.layout().addStretch(1)

  def destroy(self):
    super(TraceAndSelectOptions,self).destroy()

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
    #super(TraceAndSelectOptions,self).setMRMLDefaults()
    disableState = self.parameterNode.GetDisableModifiedEvent()
    self.parameterNode.SetDisableModifiedEvent(1)
    defaults = (
      ("maxPixels", "25000"),
      ("offsetvalue", '0'),
    )
    for d in defaults:
      param = "TraceAndSelect,"+d[0]
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
      if self.parameterNode.GetParameter("TraceAndSelect,"+p) == '':
        # don't update if the parameter node has not got all values yet
        return
    super(TraceAndSelectOptions,self).updateGUIFromMRML(caller,event)
    self.disconnectWidgets()
    self.errorMessageFrame.setText(str(self.parameterNode.GetParameter("TraceAndSelect,errorMessage")))
    self.errorMessageFrame.setStyleSheet("QTextEdit {color:blue}")
    self.errorMessageFrame.setStyleSheet(self.parameterNode.GetParameter("TraceAndSelect,errorMessageColor"))
    self.maxPixelsSpinBox.setValue( float(self.parameterNode.GetParameter("TraceAndSelect,maxPixels")) )
    self.offsetvalueSpinBox.setValue( float(self.parameterNode.GetParameter("TraceAndSelect,offsetvalue")))
    self.connectWidgets()
                                            
  def onToleranceSpinBoxChanged(self,value):
    if self.updatingGUI:
      return
    self.updateMRMLFromGUI()

  def onMaxPixelsSpinBoxChanged(self,value):
    if self.updatingGUI:
      return
    self.updateMRMLFromGUI()

  def onOffsetValueSpinBoxChanged(self,value):
    if self.updatingGUI:
      return
    self.updateMRMLFromGUI()

    
  def updateMRMLFromGUI(self):
    disableState = self.parameterNode.GetDisableModifiedEvent()
    self.parameterNode.SetDisableModifiedEvent(1)
    super(TraceAndSelectOptions,self).updateMRMLFromGUI()
    self.parameterNode.SetParameter( "TraceAndSelect,maxPixels", str(self.maxPixelsSpinBox.value) )
    self.parameterNode.SetParameter( "TraceAndSelect,offsetvalue", str(self.offsetvalueSpinBox.value) )
    self.parameterNode.SetDisableModifiedEvent(disableState)
    if not disableState:
      self.parameterNode.InvokePendingModifiedEvent()


#
# TraceAndSelectTool
#

class TraceAndSelectTool(LabelEffect.LabelEffectTool):
  """
  One instance of this will be created per-view when the effect
  is selected.  It is responsible for implementing feedback and
  label map changes in response to user input.
  This class observes the editor parameter node to configure itself
  and queries the current view for background and label volume
  nodes to operate on.
  """

  def __init__(self, sliceWidget):
    super(TraceAndSelectTool,self).__init__(sliceWidget)
    # create a logic instance to do the non-gui work
    self.logic = TraceAndSelectLogic(self.sliceWidget.sliceLogic())

  def cleanup(self):
    super(TraceAndSelectTool,self).cleanup()

  def processEvent(self, caller=None, event=None):
    """
    handle events from the render window interactor
    """

    # let the superclass deal with the event if it wants to
    if super(TraceAndSelectTool,self).processEvent(caller,event):
      return

    if event == "LeftButtonPressEvent":
      xy = self.interactor.GetEventPosition()
      sliceLogic = self.sliceWidget.sliceLogic()
      logic = TraceAndSelectLogic(sliceLogic)
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
# TraceAndSelectLogic
#

class TraceAndSelectLogic(LabelEffect.LabelEffectLogic):
  """
  This class contains helper methods for a given effect
  type.  It can be instanced as needed by an TraceAndSelectTool
  or TraceAndSelectOptions instance in order to compute intermediate
  results (say, for user feedback) or to implement the final
  segmentation editing operation.  This class is split
  from the TraceAndSelectTool so that the operations can be used
  by other code without the need for a view context.
  """

  def __init__(self,sliceLogic):
    self.sliceLogic = sliceLogic
    self.fillMode = 'Plane'


  ###
  ###
  ## START HERE ##########
  ##
  ###
  ###
  ###
  ## START HERE ##########
  ##
  ###

  def apply(self,xy):
    #
    # get the parameters from MRML
    #
    # TODO: ADD SOME KIND OF ERROR MESSAGE INTERFACE TO GUI TO PRINT THINGS LIKE UNEXPECTED SHORT PATH
    # TODO: BOUND THE FILL AREA TO A SQUARE MADE USING THE PATH EXTREMA TO LIMIT EXCESS FILLING IN THE EVENT OF ERROR
    
    # For sanity purposes, tool can always "paint" over existing labels. If we find some foreseeable reason why we might
    # not want this in all cases, we can re-add to the GUI.

    #
    # get the label and background volume nodes
    #
    labelLogic = self.sliceLogic.GetLabelLayer()
    labelNode = labelLogic.GetVolumeNode()
    backgroundLogic = self.sliceLogic.GetBackgroundLayer()
    backgroundNode = backgroundLogic.GetVolumeNode()

    ##### self.errorMessageFrame.textCursor().insertHtml('Error Detected!')
    ##### self.errorMessageFrame.setStyleSheet("QTextEdit {color:red}")

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

    ### IJK ACTIVE HERE
    #
    # Get the numpy array for the bg and label
    #
    return self.fill(ijk)

  def fill(self, ijk, optional_seeds = []):
    paintOver = 1
    mean = (0, 0)
    count = 0
    node = EditUtil.EditUtil().getParameterNode()
    
    # Max number of pixels to fill in (does not include path)
    print("@@@MaxPixels:%s" % node.GetParameter("TraceAndSelect,maxPixels"))
    maxPixels = float(node.GetParameter("TraceAndSelect,maxPixels"))
    
    # Whether or not threshold is enabled (should always be 1, since the option to disable was removed from GUI)
    print("@@@Theshold:%s" % node.GetParameter("LabelEffect,paintThreshold"))
    paintThreshold = int(node.GetParameter("LabelEffect,paintThreshold"))
    
    # Minimum intensity value to be detected
    print("@@@Theshold Min:%s" % node.GetParameter("LabelEffect,paintThresholdMin"))
    thresholdMin = float(node.GetParameter("LabelEffect,paintThresholdMin"))
    
    # Maximum intensity value to be detected
    print("@@@Theshold Max:%s" % node.GetParameter("LabelEffect,paintThresholdMax"))
    thresholdMax = float(node.GetParameter("LabelEffect,paintThresholdMax"))
  
    
    labelLogic = self.sliceLogic.GetLabelLayer()
    labelNode = labelLogic.GetVolumeNode()
    backgroundLogic = self.sliceLogic.GetBackgroundLayer()
    backgroundNode = backgroundLogic.GetVolumeNode()

    import vtk.util.numpy_support, numpy
    backgroundImage = backgroundNode.GetImageData()
    labelImage = labelNode.GetImageData()
    shape = list(backgroundImage.GetDimensions())
    shape.reverse()
    backgroundArray = vtk.util.numpy_support.vtk_to_numpy(backgroundImage.GetPointData().GetScalars()).reshape(shape)
    labelArray = vtk.util.numpy_support.vtk_to_numpy(labelImage.GetPointData().GetScalars()).reshape(shape)

    ijk_reconstruction_indexes = []
    # THIS SHOULD ALWAYS BE TRUE
    # VOLUME MODE IS DISABLED BECAUSE I HAVE NO CLUE WHAT IT IS
    original_ijk = list(ijk)
    if self.fillMode == 'Plane':
      # select the plane corresponding to current slice orientation
      # for the input volume
      ijkPlane = self.sliceIJKPlane()
      i,j,k = ijk
      if ijkPlane == 'JK':
        backgroundDrawArray = backgroundArray[:,:,k]
        labelDrawArray = labelArray[:,:,k]
        ijk = (i, j)
        ijk_reconstruction_indexes = (0,1)
      if ijkPlane == 'IK':
        backgroundDrawArray = backgroundArray[:,j,:]
        labelDrawArray = labelArray[:,j,:]
        ijk = (i, k)
        ijk_reconstruction_indexes = (0, 2)
      if ijkPlane == 'IJ':
        backgroundDrawArray = backgroundArray[i,:,:]
        labelDrawArray = labelArray[i,:,:]
        ijk = (j, k)
        ijk_reconstruction_indexes = (1,2)
    else:
        print("HOW DID YOU DO THAT??? WHAT DID YOU DO TO ACTIVATE VOLUME MODE???")
        node.SetParameter("TraceAndSelect,errorMessage", str("Error: volume mode not supported."))
        node.SetParameter("TraceAndSelect,errorMessageColor", str("QTextEdit {color:red}"))
        return


    # Log info about where the user clicked for debugging purposes
    value = backgroundDrawArray[ijk]
    print("@@@location=", ijk)
    print("@@@value=", value)
    
    # Get the current label that the user wishes to assign using the tool
    label = EditUtil.EditUtil().getLabel()
    
    # Use lo and hi for threshold checks
    # Easiest way to do things is check if a pixel is outside the threshold, ie.
    """
    try:
        b = backgroundDrawArray[(x,y)]
    except IndexError:
        NOT IN THRESHOLD (coordinates exceed bounds of array)
    if b < lo or b > hi:
       NOT IN THRESHOLD (intensity is too high or low)
    """
    lo = thresholdMin
    hi = thresholdMax
    
    location = ijk

    best_path, visited, dead_ends = gimme_a_path(ijk, 200, hi, lo, backgroundDrawArray,
                                                 optional_seeds)
    #print(best_path)
    print("Dead ends:", dead_ends)
    
    if dead_ends > 150 or dead_ends < 0:
        lo -= 25
        print("Lowering min tolerance to:", lo)
        # Too many dead ends! Let's try this again
        # TODO: reflect change in tolerance spinbox
        best_path, visited, dead_ends = gimme_a_path(ijk, 200, hi, lo, backgroundDrawArray,
                                                     optional_seeds)
        print(best_path)
        print("Dead ends:", dead_ends)
        if dead_ends < 0:
          node.SetParameter("TraceAndSelect,errorMessage", str("Error: could not find any suitable path."))
          node.SetParameter("TraceAndSelect,errorMessageColor", str("QTextEdit {color:red}"))
          return
        
    # Save state before doing anything
    self.undoRedo.saveState()
    for pixel in visited:
        labelDrawArray[pixel] = label
    
    # signal to slicer that the label needs to be updated
    # This isn't entirely necessary, but we do this here because the path has been labeled,
    # but if the path doesn't meet size requirements, we may return here
    # it's important to note that any work done without signaling an update is still saved,
    # BUT, it is not displayed until the next update
    # I don't know how costly an update is, however, for automation purposes down the line,
    # it may be to our benefit to update only once the automation across all slices is complete, rather
    # than once per slice.
    EditUtil.EditUtil().markVolumeNodeAsModified(labelNode)
    """
    if len(best_path) < 5:
        # Something went wrong
        print("@@@Path was unexpectedly short. Undoing.")
        self.undoRedo.undo()
        return
    """
    
    #
    # Fill path
    #
    fill_point = ijk
    """
    if not is_inside_path(fill_point, best_path):
        print("@@@Fill point moved from: ", fill_point)
        fill_point = get_point_inside_path(best_path)
        print("@@@to: ", fill_point)
    """
    
    # Fill the path using a recursive search
    toVisit = [fill_point,]
    # Create a map that contains the location of the pixels
    # that have been already visited (added or considered to be added).
    # This is required if paintOver is enabled because then we reconsider
    # all pixels (not just the ones that have not labelled yet).
    if paintOver:
      labelDrawVisitedArray = numpy.zeros(labelDrawArray.shape,dtype='bool')

    pixelsSet = 0
    print("@@@FILLING PATH")
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
      try:
        if (paintOver and l == label):
          temp1 = mean[0] + location[0]
          temp2 = mean[1] + location[1]
          mean = (temp1, temp2)
          count += 1
          # label is the current one, but maybe it was filled with another high/low value,
          # so we have to visit it once (and only once) in this session, too
          if  labelDrawVisitedArray[location]:
            # visited already, so don't try to fill it again
            continue
          else:
            # we'll visit this pixel now, so mark it as visited
            labelDrawVisitedArray[location] = True
      except ValueError:
        print("@@@VALUE ERROR!", l)
        print("@@@Location: ", location)
        print("@@@fill_point:", fill_point)
        print("@@@toVisit:", toVisit)
        continue
      if location in best_path:
        continue
      labelDrawArray[location] = label
      if l != label:
        # only count those pixels that were changed (to allow step-by-step growing by multiple mouse clicks)
        pixelsSet += 1
      if pixelsSet > maxPixels:
        toVisit = []
      else:
          # add the 4 neighbors to the stack
          toVisit.append((location[0] - 1, location[1]     ))
          toVisit.append((location[0] + 1, location[1]     ))
          toVisit.append((location[0]    , location[1] - 1 ))
          toVisit.append((location[0]    , location[1] + 1 ))

    # signal to slicer that the label needs to be updated
    ## CHANGE OFFSET
    print("@@@Offset:|%s|" % node.GetParameter("TraceAndSelect,offsetvalue"))
    
    self.offset = float(node.GetParameter("TraceAndSelect,offsetvalue"))
    print("OFFSET SIGN: %s" % math.copysign(1, self.offset) )

    if self.offset != 0:      
      layoutManager = slicer.app.layoutManager()
      widget = layoutManager.sliceWidget('Red')
      rednode = widget.sliceLogic().GetSliceNode()
      rednode.SetSliceOffset(rednode.GetSliceOffset() + math.copysign(1, self.offset))
      node.SetParameter("TraceAndSelect,offsetvalue", str(self.offset -  math.copysign(1, self.offset)))
      print(self.offset)
      
      ### Calc centoid mean sutff here

      recs_mean = (mean[0]/count, mean[1]/count)
      rec_mean = get_optional_seeds(best_path, recs_mean)[0]
      print("MEAN:", rec_mean, recs_mean)
      rec_ijk = list(original_ijk)
      for i in range(0,3):
        rec_ijk[i] = int(rec_ijk[i] + int(math.copysign(1, self.offset)))
      rec_ijk[ijk_reconstruction_indexes[0]] = rec_mean[0]
      rec_ijk[ijk_reconstruction_indexes[1]] = rec_mean[1]
      print("RECURSIVE IJK:", rec_ijk)
      print("#########RECURSE#########")
      return self.fill(rec_ijk, get_optional_seeds(best_path, recs_mean))
      
      ###
    
    print("@@@FILL DONE")
    EditUtil.EditUtil().markVolumeNodeAsModified(labelNode)
    node.SetParameter("TraceAndSelect,errorMessage", str("Fill complete. No errors detected."))
    node.SetParameter("TraceAndSelect,errorMessageColor", str("QTextEdit {color:Green}"))
    return

import random
  
def get_optional_seeds(seeds, mid, a= 2, b=3):
  optional_seeds = []
  maxes = [0,0]
  mins = [10000, 10000]
  for i in seeds:
    maxes[0] = max(i[0], maxes[0])
    maxes[1] = max(i[1], maxes[1])
    mins[0] = min(i[0], mins[0])
    mins[1] = min(i[1], mins[1])
    
  optional_seeds.append( (int(mid[0] + a*mins[0])/b, int(mid[1]) ))
  optional_seeds.append( ( int(mid[0]), int(mid[1] + a*mins[1])/b) )
  optional_seeds.append( (int(mid[0] + a*maxes[0])/b  ,int(mid[1])) )
  optional_seeds.append( (int(mid[0]), int(mid[1] + a*mins[1])/b) )

  return optional_seeds
  
  
def gimme_a_path(location, seed_distance, hi, lo, bgArray, optional_seeds=[]):
    """Finds the seeds, then builds the paths, then outputs the best path. No messy stuff required."""
    #
    # Find edge pixels
    #
    seeds = find_edges(location, seed_distance, hi, lo, bgArray)
    print("BEFORE", seeds)
    seeds.extend(optional_seeds)
    print("AFTER", seeds)
    #
    # Build paths
    #
    print("@@@BUILDING PATH")
    paths = []
    for seed in seeds:
        if seed is None:
            continue
        print("--- SEED ---",  str(seed))
        repeat = False
        for path in paths:
            if seed in path:
                repeat = True
            break
        if repeat:
            continue
        ret_val = build_path(seed, hi, lo, bgArray)
        if ret_val[0] == []:
            continue
        paths.append(ret_val)
    
    #
    # Find best path
    #
    best_path = find_best_path(paths, location)
    return best_path
  
  ###
  ###
  ## End HERE ##########
  ##
  ###
  ###

def find_edge(point, offset, max_dist, hi, lo, bgArray):
    """Return the first edgepoint and its distance from point using offset.
    None if no path found.
    """
    for i in range(1, max_dist):
        next = (point[0] + i * offset[0], point[1] + i * offset[1])
        if is_edge(next, hi, lo, bgArray):
            return (next, i)
    return None

def find_edges(starting_point, max_dist, hi, lo, bgArray):
    """Return an array of edge points found growing outward from starting_point.
    Search does not exceed max_dist.
    If starting_point is within threshold, find a maximum of 4 points, one for each offset.
    If starting_point is NOT within threshold, try to find as many as 8 points; two for each offset.
    """
    try:
        b = bgArray[starting_point]
    except IndexError:
        return None
    offsets = [(0,1), (1,0), (0,-1), (-1,0)]
    edgePoints = []
    for offset in offsets:
        first_result = find_edge(starting_point, offset, max_dist, hi, lo, bgArray)
        if first_result is not None:
            edgePoints.append(first_result[0])
            if b < lo or b > hi:
                # Try to find second point, since starting click was outside threshold
                second_result = find_edge(first_result[0], offset, first_result[1], hi, lo, bgArray)
                if second_result is not None:
                    edgePoints.append(second_result[0])
    return edgePoints

def build_path(start, hi, lo, bgArray):
    """Return a complete path from start."""
    dead_ends = 0
    offsets = [
        (0, 1),
        (1, 1),
        (1, 0),
        (1, -1),
        (0, -1),
        (-1, -1),
        (-1, 0),
        (-1, 1)
    ]
    visited = [start,]
    path = [start,]
    location = start
    while path != []:
        found = False
        for offset in offsets:
            neighbor = (location[0] + offset[0], location[1] + offset[1])
            if len(visited) > 1 and neighbor == start:
                # lArray[neighbor] = label
                # print("Dead ends: ", dead_ends)
                return (path, visited, dead_ends)
            if is_edge(neighbor, hi, lo, bgArray) and neighbor not in visited:
                # lArray[neighbor] = label
                visited.append(neighbor)
                path.append(neighbor)
                location = neighbor
                found = True
                break
        if not found:
            # Dead end found, re-trace steps
            # print("@@@DEAD END!")
            dead_ends += 1
            path.pop()
            if len(path) > 0:
                location = path[len(path)-1]
    print("@@@Edge is not part of the path? What the?")
    return ([],[], -1)

def find_best_path(paths, ijk):
    """Returns the best path from a list of paths ([points], [visited], dead_ends)"""
    best_path = ([],[],-1)
    best_area = 0
    for path in paths:
        extrema = get_extrema(path[0])
        # Check if ijk is likely contained within the path
        if extrema[0] < ijk[0] < extrema[1] and extrema[2] < ijk[1] < extrema[3]:
            # Create an over estimate of the approximate area of the path
            area = (extrema[1]-extrema[0])*(extrema[3]-extrema[2])
            if area > best_area:
                best_path = path
                best_area = area
    return best_path
        

def get_extrema(list):
    """Returns the max and min x and y values from a list of coordinate tuples in the form of (min_x, max_x, min_y, max_y)."""
    max_x = max(list,key=lambda item:item[0])[0]
    max_y = max(list,key=lambda item:item[1])[1]
    min_x = min(list,key=lambda item:item[0])[0]
    min_y = min(list,key=lambda item:item[1])[1]
    return (min_x, max_x, min_y, max_y)

def is_edge(location, hi, lo, bgArray):
    """Return true is location is an edge pixel."""
    offsets = [
        (0,1),
        (1,0),
        (0,-1),
        (-1,0)
    ]
    # Check that location is within threshold first
    try:
        b = bgArray[location]
    except IndexError:
        return False
    if b < lo or b > hi:
        return False
    
    # Check if its neighbors are outside the threshold
    for offset in offsets:
        tmp = (location[0] + offset[0], location[1] + offset[1])
        try:
            b = bgArray[tmp]
        except IndexError:
            return True
        if b < lo or b > hi:
            return True
    return False


def is_inside_path(location, path):
    """Return true if location is inside path."""
    # Check that location is not in path
    if location in path:
        return False
    # Check the number of edge points between the point and each edge of the DICOM
    # Multiple checks necessary to avoid edge cases where an edge of the path may be parallel to an axis
    # Ex:
    """
     #######
    #      #E
    ##  P   #
      ######
    """
    # If the number of intersections from negative x-axis were counted, P would be considered outside the path.
    # TODO:
    # EDGE CASE: E IS CONSIDERED INSIDE THE SHAPE
    # Modify so that the function checks all 4 axes, and only proceeds if the number of intersections is correct for ALL of them.
    # Will have to make it so it doesn't simply sum intersection points, but will have to ignore series of contiguous points and count them as a single intersection.
    intersections = sum(x[0] == location[0] and x[1] < location[1] for x in path)
    if (intersections % 2) == 1:
        return True
    intersections = sum(x[0] == location[0] and x[1] > location[1] for x in path)
    if (intersections % 2) == 1:
        return True
    intersections = sum(x[1] == location[1] and x[0] < location[0] for x in path)
    if (intersections % 2) == 1:
        return True
    intersections = sum(x[1] == location[1] and x[0] > location[0] for x in path)
    if (intersections % 2) == 1:
        return True
    return False


def get_point_inside_path(path):
    """Return a point inside the path."""
    point = path[0]
    offsets = [
        (0,1),
        (1,0),
        (0,-1),
        (-1,0)
    ]
    for offset in offsets:
        tmp = (point[0] + offset[0], point[1] + offset[1])
        if is_inside_path(tmp, path):
            return tmp
    print("@@@There are no adjacent points inside the path???")
    return None

#
# The TraceAndSelect class definition
#

class TraceAndSelectExtension(LabelEffect.LabelEffect):
  """Organizes the Options, Tool, and Logic classes into a single instance
  that can be managed by the EditBox
  """

  def __init__(self):
    # name is used to define the name of the icon image resource (e.g. TraceAndSelect.png)
    self.name = "TraceAndSelect"
    # tool tip is displayed on mouse hover
    self.toolTip = "Paint: circular paint brush for label map editing"

    self.options = TraceAndSelectOptions
    self.tool = TraceAndSelectTool
    self.logic = TraceAndSelectLogic

""" Test:

sw = slicer.app.layoutManager().sliceWidget('Red')
import EditorLib
pet = EditorLib.TraceAndSelectTool(sw)

"""

#
# TraceAndSelect
#

class TraceAndSelect:
  """
  This class is the 'hook' for slicer to detect and recognize the extension
  as a loadable scripted module
  """
  def __init__(self, parent):
    parent.title = "Editor TraceAndSelect Effect"
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
    slicer.modules.editorExtensions['TraceAndSelect'] = TraceAndSelectExtension

#
# TraceAndSelectWidget
#

class TraceAndSelectWidget:
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
