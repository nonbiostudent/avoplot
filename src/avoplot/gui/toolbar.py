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
import wx
import functools
from matplotlib.backends.backend_wx import _load_bitmap as load_matplotlib_bitmap

from avoplot import core
from avoplot import drawing
from avoplot import figure
from avoplot import subplots
from avoplot.gui import menu

class MainToolbar(wx.ToolBar):
    """
    Main program toolbar
    """
    def __init__(self,parent):
        self.parent = parent
        
        self.__active_figure = None
        self.__all_figures = set()
        
        wx.ToolBar.__init__(self,parent, wx.ID_ANY)
        
        #file tools    
        self.new_tool = self.AddTool(-1, wx.ArtProvider.GetBitmap(wx.ART_NEW, wx.ART_TOOLBAR), shortHelpString="New plot")    
        self.save_tool = self.AddTool(-1, wx.ArtProvider.GetBitmap(wx.ART_FILE_SAVE, wx.ART_TOOLBAR), shortHelpString="Save plot")
        self.AddSeparator()

        #plot navigation tools
        self.home_tool = self.AddTool(-1, wx.ArtProvider.GetBitmap(wx.ART_GO_HOME, wx.ART_TOOLBAR),shortHelpString="Return to initial zoom setting")
        self.back_tool =  self.AddTool(-1, load_matplotlib_bitmap('back.png'), shortHelpString="Previous zoom setting")
        self.forward_tool = self.AddTool(-1, load_matplotlib_bitmap('forward.png'), shortHelpString="Next zoom setting")
        self.zoom_tool = self.AddCheckTool(-1, load_matplotlib_bitmap('zoom_to_rect.png'), shortHelp="Zoom selection")
        self.pan_tool = self.AddCheckTool(-1, load_matplotlib_bitmap('move.png'),shortHelp='Pan',longHelp='Pan with left, zoom with right')
        self.AddSeparator()
        self.add_subplot_tool = self.AddTool(-1, wx.ArtProvider.GetBitmap("avoplot_newsubplot", wx.ART_TOOLBAR),shortHelpString='Add subplot')
        
        self.Realize()
        self.enable_plot_tools(False)
        
        #register avoplot event handlers
        core.EVT_AVOPLOT_ELEM_ADD(self, self.on_element_add)
        core.EVT_AVOPLOT_ELEM_SELECT(self, self.on_element_select)
        core.EVT_AVOPLOT_ELEM_DELETE(self, self.on_element_delete)
        
        #register events
        wx.EVT_TOOL(self.parent, self.new_tool.GetId(), self.on_new)
        wx.EVT_TOOL(self.parent, self.save_tool.GetId(), self.on_save_plot)        
        wx.EVT_TOOL(self.parent, self.home_tool.GetId(), self.on_home)
        wx.EVT_TOOL(self.parent, self.back_tool.GetId(), self.on_back)
        wx.EVT_TOOL(self.parent, self.forward_tool.GetId(), self.on_forward)
        wx.EVT_TOOL(self.parent, self.zoom_tool.GetId(), self.on_zoom)
        wx.EVT_TOOL(self.parent, self.pan_tool.GetId(), self.on_pan)
        wx.EVT_TOOL(self.parent, self.add_subplot_tool.GetId(), self.on_add_subplot)
    
    
    def on_element_add(self, evnt):
        """
        Event handler for new element events. If the element is not a figure
        then nothing gets done. For figures, their zoom and pan settings are
        updated depending on the toggle state of the zoom/pan tools.
        
        This method also enables the plot navigation tools if they were 
        previously disabled.
        """
        el = evnt.element
        if isinstance(el, figure.AvoPlotFigure):
            if not self.__all_figures:
                self.enable_plot_tools(True)
            
            self.__active_figure = el
            
            #enable the zoom/pan tools for this figure (if they are currently
            #selected in the toolbar)
            if self.GetToolState(self.pan_tool.GetId()):
                el.pan()
            elif self.GetToolState(self.zoom_tool.GetId()):
                el.zoom()
            
            self.__all_figures.add(el)
            
            #initialise the pan and zoom tools to "off" each time a new figure 
            #is created
            self.set_zoom_state(False)
            self.set_pan_state(False)
    
    
    def on_element_delete(self, evnt):
        """
        Event handler for element delete events.If the element is not a figure
        then nothing gets done. If the element being deleted was the last figure
        in the session, then this disables the plot navigation tools. 
        """
        el = evnt.element
        if isinstance(el, figure.AvoPlotFigure):
            self.__all_figures.remove(el)
            if not self.__all_figures:
                self.__active_figure = None
                self.enable_plot_tools(False)
                
    
    def on_element_select(self, evnt):
        """
        Event handler for element select events. Keeps track of what the 
        currently selected element is and updates the state of the history 
        buttons.
        """
        el = evnt.element
        if isinstance(el, figure.AvoPlotFigure):
            self.__active_figure = el
            
            #set the history button update handler so that the history buttons
            #get enabled/disabled at the correct times
            self.__active_figure.tb.set_history_buttons = self.update_history_buttons
            
            self.update_history_buttons()
        
    
    
    def enable_plot_tools(self, state):
        """
        Enables the plot tools if state=True or disables them if state=False
        """
        self.EnableTool(self.save_tool.GetId(),state)
        self.EnableTool(self.home_tool.GetId(),state)
        self.EnableTool(self.pan_tool.GetId(),state)
        self.EnableTool(self.zoom_tool.GetId(),state)
        self.EnableTool(self.add_subplot_tool.GetId(), state)
        
        self.update_history_buttons()

   
    
    def on_new(self,evnt):
        """Handle 'new' button pressed.
        Creates a popup menu over the tool button containing the same entries as
        the File->New menu.
        """
        #Get the position of the toolbar relative to
        #the frame. This will be the upper left corner of the first tool
        bar_pos = self.GetScreenPosition()-self.parent.GetScreenPosition()

        # This is the position of the tool along the tool bar (1st, 2nd, 3rd, etc...)
        tool_index = self.GetToolPos(evnt.GetId())

        # Get the size of the tool
        tool_size = self.GetToolSize()

        # This is the lower left corner of the clicked tool
        lower_left_pos = (bar_pos[0]+self.GetToolSeparation()*(tool_index+1)+tool_size[0]*tool_index, bar_pos[1]+tool_size[1]+self.GetToolSeparation())#-tool_size[1])

        menu_pos = (lower_left_pos[0]-bar_pos[0],lower_left_pos[1]-bar_pos[1])
        self.PopupMenu(menu.create_the_New_menu(self.parent), menu_pos)

        
    def on_home(self, evnt):
        """
        Event handler for "home zoom level" events. Resets all subplots in the 
        current figure to their default zoom levels.
        """
        if self.__active_figure is not None:
            self.__active_figure.go_home()
 
 
    def on_back(self, evnt):
        """
        Event handler for 'back' tool events. Returns the figure to its previous
        view.
        """
        if self.__active_figure is not None:
            self.__active_figure.back()
            
    
    def on_forward(self, evnt):
        """
        Event handler for 'forward' tool events. Returns the figure to its next
        view.
        """
        if self.__active_figure is not None:
            self.__active_figure.forward()
    
            
    def on_zoom(self,evnt):
        """
        Event handler for zoom tool toggle events. Enables or disables zooming
        in all figures accordingly.
        """
        self.set_zoom_state(self.GetToolState(self.zoom_tool.GetId()))
    
    
    def set_zoom_state(self, state):
        """
        Enables (state = True) or disables (state = False) the zoom tool for all
        figures. The pan tool will be disabled if needed.
        """
        self.ToggleTool(self.zoom_tool.GetId(),state)
        
        if state:
            self.ToggleTool(self.pan_tool.GetId(),False)
        
        for p in self.__all_figures:
            if p.is_zoomed() != state:
                p.zoom()
   
   
    def set_pan_state(self, state):
        """
        Enables (state = True) or disables (state = False) the pan tool for all
        figures. The zoom tool will be disabled if needed.
        """
        self.ToggleTool(self.pan_tool.GetId(),state)
        
        if state:
            self.ToggleTool(self.zoom_tool.GetId(),False)
        
        for p in self.__all_figures:
            if p.is_panned() != state:
                p.pan()
   
   
    def on_pan(self,evnt):
        """
        Event handler for pan tool toggle events. Enables or disables panning
        in all figures accordingly.
        """
        self.set_pan_state(self.GetToolState(self.pan_tool.GetId()))

    
    def on_save_plot(self, *args):
        """
        Event handler for save tool events. Opens a file save dialog for saving
        the currently selected figure as an image file.
        """
        if self.__active_figure is not None:
            self.__active_figure.save_figure_as_image()
    
        
    def on_add_subplot(self, evnt):
        """
        Event handler for add subplot tool events. Changes the cursor to a cross, and
        allows the user to draw an area which becomes the subplot.
        """
        #generate a menu of all the available subplot types
        types_and_names = subplots.get_subplot_types_and_names()
        
        menu = wx.Menu()      
        sub_menus = {}
        
        for t_and_n in types_and_names:
            labels = t_and_n[1]
            
            cur_submenu = menu
            cur_submenu_dict = sub_menus
            
            for i in range(len(labels)-1):
                
                if not cur_submenu_dict.has_key(labels[i]):
                    cur_submenu_dict[labels[i]] = ({},wx.Menu())
                    cur_submenu.AppendSubMenu(cur_submenu_dict[labels[i]][1], 
                                              labels[i]) 
                    
                cur_submenu = cur_submenu_dict[labels[i]][1]
                cur_submenu_dict = cur_submenu_dict[labels[i]][0]
            
            #TODO - add tooltip for subplot type
            entry = cur_submenu.Append(-1, labels[-1], "")
                                           #p.get_menu_entry_tooltip())
            
            callback_func = functools.partial(self.__on_add_subplot_menu_callback, subplot_type=t_and_n[0])
            #callback_func = lambda x: self.__on_add_subplot_menu_callback(x, t_and_n[0])
            wx.EVT_MENU(self, entry.GetId(), callback_func)
        
        #Get the position of the toolbar relative to
        #the frame. This will be the upper left corner of the first tool
        bar_pos = self.GetScreenPosition()-self.parent.GetScreenPosition()

        # This is the position of the tool along the tool bar (1st, 2nd, 3rd, etc...)
        tool_index = self.GetToolPos(evnt.GetId())

        # Get the size of the tool
        tool_size = self.GetToolSize()

        # This is the lower left corner of the clicked tool
        lower_left_pos = (bar_pos[0]+self.GetToolSeparation()+tool_size[0]*(tool_index), bar_pos[1]+tool_size[1]+self.GetToolSeparation())#-tool_size[1])
        
        menu_pos = (lower_left_pos[0]-bar_pos[0],lower_left_pos[1]-bar_pos[1])
        self.PopupMenu(menu, menu_pos)
        
    
    def __on_add_subplot_menu_callback(self, evnt, subplot_type=None):
        
        self.enable_plot_tools(False)
        
        callback_function = lambda rect: self.__on_add_subplot_callback(rect, subplot_type)
        self.__subplot_add_selection_tool = drawing.RectRegionSelect(self.__active_figure, callback=callback_function)
        self.__subplot_add_selection_tool.enable_selection()
    
    
    def __on_add_subplot_callback(self, rect, subplot_class):
        
        self.__subplot_add_selection_tool.disable_selection()
        self.enable_plot_tools(True)
        
        if abs(rect[0]-rect[2]) > 0.2 or abs(rect[1]-rect[3]) > 0.2:
            subplot = subplot_class(self.__active_figure, 
                                    rect=(rect[0],rect[1],rect[2]-rect[0], 
                                          rect[3]-rect[1]))
            self.__active_figure.update()
        
        
    def update_history_buttons(self):
        """
        Enables/disables the next- and prev-view buttons depending on whether
        there are views to go forward or back to.
        """
        if self.__active_figure is not None:
            current_mpl_toolbar = self.__active_figure.tb
            can_backward = (current_mpl_toolbar._views._pos > 0)  
            can_forward = (current_mpl_toolbar._views._pos < len(current_mpl_toolbar._views._elements) - 1)
        else:
            can_backward = False
            can_forward = False
            
        self.EnableTool(self.back_tool.GetId(),can_backward)
        self.EnableTool(self.forward_tool.GetId(),can_forward)
        