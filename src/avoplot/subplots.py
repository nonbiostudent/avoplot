#Copyright (C) Nial Peters 2013
#
#This file is part of AvoPlot.
#
#AvoPlot is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#AvoPlot is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with AvoPlot.  If not, see <http://www.gnu.org/licenses/>.

from avoplot.figure import AvoPlotFigure
import matplotlib.colors
import avoplot.gui.gridlines
from avoplot.gui import widgets
from avoplot import core
from avoplot import figure
from avoplot import controls
from avoplot import plugins
import threading
import time
import wx
import numpy
from wx.lib.agw import floatspin


class MetaCallMyInit(type):
    """
    Metaclass which ensures that a class's my_init() 
    method gets called once, after it's __init__ method has returned.
    """
    def __call__(self, *args, **kw):
        obj=type.__call__(self, *args, **kw)
        obj.my_init()
        return obj



class AvoPlotSubplotBase(core.AvoPlotElementBase):
    """
    The AvoPlotSubplotBase class is the base class for all subplots - which 
    represent a set of axes in the figure.
    """
    
    #metaclass ensures that my_init() is called once, after __init__ method
    #has completed. This requires a metaclass, because if the class is 
    #subclassed then there is a danger of my_init() being called multiple times
    #or being called before all the base class' __init__ methods have been 
    #called
    __metaclass__ = MetaCallMyInit
    
    def __init__(self, fig, name='subplot'):
        super(AvoPlotSubplotBase, self).__init__(name)
        self.set_parent_element(fig)
    
    
    def add_data_series(self, data):
        """
        Adds a data series to the subplot. data should be an instance of
        avoplot.series.DataSeriesBase or a subclass.
        """
        #assert isinstance(data, series.DataSeriesBase)
        data.set_parent_element(self)
        
        
    def set_parent_element(self, parent):
        """
        Overrides the AvoPlotElementBase class's method. Does the exactly
        the same as the base class but ensures that the parent is an 
        AvoPlotFigure instance.
        """
        assert isinstance(parent, AvoPlotFigure) or parent is None
        super(AvoPlotSubplotBase, self).set_parent_element(parent)
          
                     
    def my_init(self):
        """
        This method should be overridden by subclasses wishing to customise the
        look of the subplot before it is displayed.
        """
        pass
    
    
    def get_figure(self):
        """
        Returns the AvoPlotFigure instance that this subplot is contained 
        within , or None if the series does not yet belong to a figure. Use 
        get_figure().get_mpl_figure() to get the matplotlib figureobject that 
        the subplot is associated with.
        """
        #look up the list of parents recursively until we find a figure object
        parent = self.get_parent_element()
        while not isinstance(parent, figure.AvoPlotFigure):
            if parent is None:
                return None
            parent = parent.get_parent_element()
            
            #sanity check - there should always be a figure object somewhere
            #in the ancestry of a series object.
            if isinstance(parent, core.AvoPlotSession):
                raise RuntimeError("Reached the root element before an "
                                   "AvoPlotFigure instance was found.")
        return parent
    
    
#     def on_mouse_button(self, evnt):
#         """
#         Event handler for mouse click events. These will be passed to the
#         subplot from its parent figure. This should be overriden by subclasses.
#         """
#         pass
        
        

class AvoPlotXYSubplot(AvoPlotSubplotBase):
    """
    Subplot for containing 2D (XY) data series.
    """
    def __init__(self, fig, name='xy subplot', rect=(0.12,0.1,0.8,0.8)):
        super(AvoPlotXYSubplot, self).__init__(fig, name=name)
        
        #note the use of self.get_name() to ensure that the label is unique!
        self.__mpl_axes = fig.get_mpl_figure().add_axes(rect, label=self.get_name())
        
        self.add_control_panel(XYSubplotControls(self))
        
        self.__mpl_axes.set_picker(5.0)
        
        
    def get_mpl_artists(self):
        """
        Overrides base class method in order to associate the subplot element 
        with its matplotlib axes.
        """
        return [self.get_mpl_axes()]
    
    
    def delete(self):
        """
        Overrides base class delete method in order to remove the axes from 
        the figure and draw the changes.
        """
        ax = self.get_mpl_axes()
        fig = self.get_parent_element()
        
        if fig is not None:
            mpl_fig = fig.get_mpl_figure()
        
            mpl_fig.delaxes(ax)
        
            fig.update()
        
        super(AvoPlotXYSubplot, self).delete()
        
        
    def get_mpl_axes(self):
        """
        Returns the matplotlib axes object associated with this subplot.
        """
        return self.__mpl_axes  
    

#     def on_mouse_button(self, evnt):
#         """
#         Event handler for mouse click events.
#         """
#         if evnt.inaxes != self.__mpl_axes: 
#             return
#         
#         if evnt.button ==3:
#             wx.CallAfter(self.on_right_click)
#             #need to release the mouse otherwise everything hangs (under Linux at
#             #least)
#             self.get_figure().GetCapture().ReleaseMouse()
#             return

      
    def on_right_click(self):
        """
        Called by on_mouse_button() if the event was a right-click. Creates
        a PopupMenu for adding new data series to the subplot.
        """
        menu = avoplot.gui.menu.get_subplot_right_click_menu(self)
        
        #need to release the mouse otherwise everything hangs (under Linux at
        #least)
        cap = self.get_figure().GetCapture()
        if cap is not None:
            cap.ReleaseMouse()
        
        
        wx.CallAfter(self.get_figure().PopupMenu, menu)
        #menu.Destroy()
        
        
    
    
    def add_data_series(self, data):
        """
        Adds (i.e. plots) a data series into the subplot. data should be an
        avoplot.series.XYDataSeries instance or subclass thereof.
        """
        super(AvoPlotXYSubplot, self).add_data_series(data)
        data._plot(self)
        self.update()
        
    
    def update(self):
        """
        Redraws the subplot.
        """
        fig = self.get_figure()
        if fig is not None:
            canvas = fig.canvas
            if canvas:
                canvas.draw()
        


class XYSubplotControls(controls.AvoPlotControlPanelBase):
    """
    Control panel for allowing the user to edit subplot parameters (title,
    axis labels etc.). The subplot argument should be an AvoPlotXYSubplot
    instance.
    """
    
    def __init__(self, subplot):
        super(XYSubplotControls, self).__init__("Subplot")
        self.subplot = subplot
    
    
    def setup(self, parent):
        """
        Creates all the controls for the panel.
        """
        super(XYSubplotControls, self).setup(parent)
        
        ax = self.subplot.get_mpl_axes()
        
        #title box
        title = widgets.TextSetting(self, 'Title:', ax.title)  
        self.Add(title, 0, wx.ALIGN_LEFT|wx.EXPAND|wx.ALL, border=10) 
        
        #background colour selection
        bkgd_col = ax.get_axis_bgcolor()
        bkgd_col = matplotlib.colors.colorConverter.to_rgb(bkgd_col)
        bkgd_col = (255 * bkgd_col[0], 255 * bkgd_col[1], 255 * bkgd_col[2])
        colour = widgets.ColourSetting(self, 'Fill:', bkgd_col,
                                       self.on_bkgd_colour)
        self.Add(colour, 0, wx.ALIGN_RIGHT|wx.LEFT|wx.RIGHT, border=10) 
        
        #background opacity
        alpha = ax.patch.get_alpha()
        if not alpha:
            alpha = 1.0
        self.alpha_ctrl = floatspin.FloatSpin(self, -1,min_val=0.0, max_val=1.0,
                                              value=alpha, increment=0.1, 
                                              digits=1)
        alpha_txt = wx.StaticText(self, wx.ID_ANY, "Opacity:")
        
        alpha_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        alpha_sizer.Add(alpha_txt, 0,wx.ALIGN_CENTRE_VERTICAL | wx.ALIGN_RIGHT)
        alpha_sizer.Add(self.alpha_ctrl, 0, wx.ALIGN_CENTRE_VERTICAL | wx.ALIGN_LEFT)
        self.Add(alpha_sizer, 0, wx.ALIGN_RIGHT|wx.LEFT|wx.RIGHT, border=10)
        
        floatspin.EVT_FLOATSPIN(self, self.alpha_ctrl.GetId(), self.on_alpha_change)    

        #x-axis controls
        x_axis_ctrls_szr = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, 'x-axis'), wx.VERTICAL)
        xlabel = widgets.TextSetting(self, 'Label:', ax.xaxis.label)        
        x_axis_ctrls_szr.Add(xlabel, 0, wx.ALIGN_LEFT|wx.EXPAND|wx.ALL, border=10)
        
        x_axis_ctrls_szr.Add(GridLinesCheckBox(self, ax.xaxis, self.subplot), 0 , wx.ALIGN_LEFT| wx.LEFT, border=10)
        
        xtick_labels_chkbox = TickLabelsCheckBox(self, ax.xaxis)
        xtick_labels_chkbox.set_checked(True)
        x_axis_ctrls_szr.Add(xtick_labels_chkbox, 0 , wx.ALIGN_LEFT| wx.LEFT| wx.BOTTOM, border=10)
        self.Add(x_axis_ctrls_szr, 0, wx.EXPAND|wx.ALL, border=5)
        
        
        #y-axis controls
        y_axis_ctrls_szr = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, 'y-axis'), wx.VERTICAL)
        ylabel = widgets.TextSetting(self, 'Label:', ax.yaxis.label)        
        y_axis_ctrls_szr.Add(ylabel, 0, wx.ALIGN_LEFT|wx.EXPAND|wx.ALL, border=10)
        
        y_axis_ctrls_szr.Add(GridLinesCheckBox(self, ax.yaxis, self.subplot), 0 , wx.ALIGN_LEFT| wx.LEFT, border=10)
        
        ytick_labels_chkbox = TickLabelsCheckBox(self, ax.yaxis)
        ytick_labels_chkbox.set_checked(True)
        y_axis_ctrls_szr.Add(ytick_labels_chkbox, 0 , wx.ALIGN_LEFT| wx.LEFT | wx.BOTTOM, border=10)
        
        self.Add(y_axis_ctrls_szr, 0, wx.EXPAND|wx.ALL, border=5)        
    
    
    def on_alpha_change(self, evnt):
        """
        Event handler for changes in the background opacity.
        """
        self.subplot.get_mpl_axes().patch.set_alpha(self.alpha_ctrl.GetValue())
        self.subplot.update()
    
    
    def on_display(self):
        """
        On Windows, parts of the control panel do not draw correctly unless you
        send a size event - so we do that here.
        
        This is called automatically when the control panel is displayed (see
        baseclass docstring).
        """
        self.SendSizeEvent()
    
    
    def on_bkgd_colour(self, evnt):
        """
        Event handler for the background colour selector.
        """
        ax = self.subplot.get_mpl_axes()
        ax.set_axis_bgcolor(evnt.GetColour().GetAsString(wx.C2S_HTML_SYNTAX))
        self.subplot.update()
            

class InspectableXYSubplot(AvoPlotXYSubplot):
    def __init__(self, *args, **kwargs):
        super(InspectableXYSubplot, self).__init__(*args, **kwargs)
        self.cids=[]
        self._selected_points = []
        self._selection_lines = []
        self.cursor_vline = None
        self.background = None
        self.ax = self.get_mpl_axes()
        
        self.figure = self.get_figure()
        self.canvas = None
        self.__enabled = False
    
    
    def on_selection(self, idx):
        """
        Should be defined by subclasses - this is called whenever the user
        selects a point in the subplot.
        """
        pass
    
    def clear_selection(self):
        """
        Clear the current selection
        """
        for l in self._selection_lines:
            l.remove()
            
        self._selected_points = []
        self._selection_lines = []
        self.update()
    
    
    def ignore(self, event):
        'Returns True if event should be ignored, false otherwise'
        return  (self.figure.is_zoomed() or
                 self.figure.is_panned() or
                 event.inaxes!=self.ax or 
                 not self.visible)
    
    
    def enable_selection(self):
        """
        Enables or disables the selection functionality.
        """
        if self.__enabled:
            return
        self.__enabled = True
        self.series = list(self.get_child_elements())[0]
        self.visible = True
        
        #register the event handlers
        self.canvas = self.ax.figure.canvas
        self.cids.append(self.canvas.mpl_connect('motion_notify_event', self.on_move))
        self.cids.append(self.canvas.mpl_connect('button_press_event', self.on_click))
        self.cids.append(self.canvas.mpl_connect('draw_event', self.on_draw))
        
        #disable the pan and zoom controls
        fig = self.get_figure()
        fig.enable_pan_and_zoom_tools(False)
        fig.enable_picking(False)  
        
        
        
        self.cursor_vline = self.ax.axvline(self.ax.get_xbound()[0], linewidth=1, color=(0,0,0),
                                               animated=True)  
    
    def disable_selection(self):
        """
        Disables the selection tool - disconnecting the matplotlib canvas 
        callbacks and clearing any current selection.
        """
        self.__enabled = False
        
        for cid in self.cids:
                self.canvas.mpl_disconnect(cid)
        self.cids = []
        self.visible = False
        
        #remove the cursor lines from the subplot
        
        if self.cursor_vline is not None:
            self.cursor_vline.remove()
            self.cursor_vline = None
        
        #remove any current selection
        self.clear_selection()
        
        #since the on_draw callback is now diasbled - need to clear the 
        #background cache
        self.background = None
        
        self.figure.enable_picking(True)
    
    
    def on_draw(self, evnt):
        """
        Callback handler for draw events. Re-caches the background for future 
        blitting and redraws the selection rectangles.
        """
        self.update_background()
        self.update_animated()
            
    
    def update_background(self):
        """
        Re-caches the backgound.
        """
        self.background = self.canvas.copy_from_bbox(self.ax.bbox)
   
   
    def on_click(self, event):
        if self.ignore(event) or event.button !=1: 
            return
        
        if not event.guiEvent.ControlDown() and self._selected_points:
            self.clear_selection()
        
        if self.background is None:
            self.update_background()
        
        xdata, ydata = self.series.get_data()
        data_loc = numpy.argmin(numpy.fabs(xdata - event.xdata))
        
        l = self.ax.axvline(xdata[data_loc], linewidth=2)
        
        self._selection_lines.append(l)
        self._selected_points.append(data_loc)
        self.on_selection(self._selected_points)
        self.update()
    
    def get_selection(self):
        return [i for i in self._selected_points]
    
        
    def set_selection(self, xidx):
        xdata, ydata = self.series.get_data()
        
        l = self.ax.axvline(xdata[xidx], linewidth=2)
        
        self._selection_lines.append(l)
        self._selected_points.append(xidx)
        self.on_selection(self._selected_points)
        self.update()
    
        
    def on_move(self, event):
        """
        Event handler for mouse move events.
        """
        if self.ignore(event):
            update_flag = False
            if self.cursor_vline is not None and self.cursor_vline.get_visible():
                #move the cursor into the normal axis lims so that it doesn't 
                #mess up relim() if the home button is clicked
                centre_x = sum(self.get_mpl_axes().get_xlim())/2
                self.cursor_vline.set_xdata([centre_x,centre_x])                
                
                update_flag = True
                self.cursor_vline.set_visible(False)
                
            if update_flag:
                self.update_animated()
            return
        
        if self.background is None:
            self.update_background()    
        
        x, y = event.xdata, event.ydata
            
        if self.cursor_vline is not None:
            self.cursor_vline.set_visible(True)
            self.cursor_vline.set_xdata([x,x])
        
        self.update_animated()
        return
    
    def update_animated(self):
        if self.canvas is None:
            return
        
        if self.background is not None:
            self.canvas.restore_region(self.background)
        
        if self.cursor_vline is not None:
            self.ax.draw_artist(self.cursor_vline)
            
        self.canvas.blit(self.ax.bbox)    
    
        
    
class GridLinesCheckBox(avoplot.gui.widgets.EditableCheckBox):
    
    def __init__(self, parent, mpl_axis, subplot):
        
        avoplot.gui.widgets.EditableCheckBox.__init__(self, parent, "Gridlines")
        self.mpl_axis = mpl_axis
        self.subplot = subplot
    
    
    def on_checkbox(self, evnt):
        """
        Event handler for the gridlines checkbox.
        """
        self.mpl_axis.grid(b=evnt.IsChecked())
        self.mpl_axis.figure.canvas.draw()
  
            
    def on_edit_link(self, evnt):
        avoplot.gui.gridlines.GridPropertiesEditor(self.parent, self.subplot, 
                                                   self.mpl_axis)  
  
  
        
class TickLabelsCheckBox(avoplot.gui.widgets.EditableCheckBox):
    
    def __init__(self, parent, mpl_axis):
        
        avoplot.gui.widgets.EditableCheckBox.__init__(self, parent, 
                                                      "Tick labels")
        self.mpl_axis = mpl_axis
    
    
    def on_checkbox(self, evnt):
        for label in self.mpl_axis.get_ticklabels():
            label.set_visible(evnt.IsChecked())
        self.mpl_axis.figure.canvas.draw()
    
    
    def on_edit_link(self, evnt):
        avoplot.gui.text.TextPropertiesEditor(self.parent, 
                                              self.mpl_axis.get_ticklabels())
        

class RealtimeXYSubplot(AvoPlotXYSubplot):
    
    def __init__(self, fig, name='xy subplot', rect=(0.12,0.1,0.8,0.8)):
        self._background = None
        self.__cids = []
        self.stay_alive = True
        self.update_interval = 0.0
        self.__pending_callafter_finish = threading.Event() 
        self.__update_required = threading.Event() 
        self.__pending_callafter_finish.set()
        self.plotting_thread = threading.Thread(target=self._update_plot)
        self.plotting_thread.start()
        super(RealtimeXYSubplot, self).__init__(fig, name=name, rect=rect)
    
    def my_init(self):
        super(RealtimeXYSubplot,self).my_init()
        wx.CallAfter(self.__register_callback)
        
    
    def __register_callback(self):
        canvas = self.get_figure().get_mpl_figure().canvas
        if canvas is not None:
            self.__cids.append(canvas.mpl_connect('draw_event', self.on_draw))
    
           
    def delete(self):
        self.stay_alive = False
        self.request_update() #unblock the update thread
        
        if self.plotting_thread.is_alive():
            self.plotting_thread.join()
            
        fig = self.get_figure()
        if fig is not None:
            canvas = fig.get_mpl_figure().canvas
            if canvas is not None:
                for cid in self.__cids:
                    canvas.mpl_disconnect(cid)
        
        super(RealtimeXYSubplot, self).delete()
    
    
    def request_update(self):
        self.__update_required.set()
    
    
    def _update_plot(self):
        while self.stay_alive:
            if self.__pending_callafter_finish.is_set():
                self.__pending_callafter_finish.clear()
                wx.CallAfter(self.__update)
            time.sleep(self.update_interval)
            
            self.__update_required.wait()
            self.__update_required.clear()
        
        #don't bother waiting for pending CallAfter calls to finish - just let
        #them fail (if we get to here then the plot is being deleted anyway)
    
    
    def __update(self):
        try:
            if self.stay_alive:
                self.update_animated()
        finally:    
            self.__pending_callafter_finish.set()
            
            
    def add_data_series(self, series):
        wx.CallAfter(super(RealtimeXYSubplot,self).add_data_series,series)
    
    
    def on_draw(self, evnt):
        self._update_background()
        self.update_animated()
    
    
    def update(self):
        super(RealtimeXYSubplot,self).update()

        #refresh the pixel buffer
        self._update_background()
        
        #draw in the animated components
        self.update_animated()
        
    
    def update_animated(self):
        fig = self.get_figure()
        
        if fig is None or fig.canvas is None:
            return
        
        if self._background is None:
            self._update_background()
        
        ax = self.get_mpl_axes()
        
        fig.canvas.restore_region(self._background)
        
        for a in ax.lines:
            if a.get_animated():
                ax.draw_artist(a)
        
        fig.canvas.blit(ax.bbox)
    
    
    def _update_background(self):
        fig = self.get_figure()
        
        if fig is not None and fig.canvas is not None:
            mpl_ax = self.get_mpl_axes()
        
            self._background = fig.canvas.copy_from_bbox(mpl_ax.bbox)
    



def get_subplot_types_and_names():
    """
    Returns a list of (subplot class, [menu entry lables]) tuples containing all
    the unique subplot types that are currently registered.
    """   
    all_plugins = plugins.get_plugins().values()
    
    #hardcode in XYSubplot (since don't want fromFile plugin to show up)
    types_and_names = [(AvoPlotXYSubplot, ["Basic XY Plot"])]
    unique_subplots = [AvoPlotXYSubplot]
    
    for p in all_plugins:
        subplot_type = p.get_supported_series_type().get_supported_subplot_type()
        
        if subplot_type not in unique_subplots:
            unique_subplots.append(subplot_type)
            labels = p.get_menu_entry_labels()
            types_and_names.append((subplot_type, labels))
    
    return types_and_names
            
            