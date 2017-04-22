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
from wx.lib.agw import aui

from avoplot import figure
from avoplot import core
from avoplot.gui import menu
import avoplot


class PlotsPanel(aui.AuiNotebook):
    """
    AuiNotebook for displaying figures in. Multiple figures may be viewed 
    simultaneously by splitting the notebook.
    """
    
    def __init__(self, parent):
        aui.AuiNotebook.__init__(self, parent, id=wx.ID_ANY, 
                                 agwStyle=aui.AUI_NB_TAB_SPLIT|aui.AUI_NB_CLOSE_ON_ALL_TABS)
        
        self._tab_menu = menu.TabRightClickMenu(self)
        
        self.__mplartist_to_element_map = {}
        
        self.__picking_enabled = False
        self.__pick_evnts_to_process = []
        
        #register avoplot event handlers
        core.EVT_AVOPLOT_ELEM_SELECT(self, self.on_select_element)
        core.EVT_AVOPLOT_ELEM_ADD(self, self.on_new_element)
        core.EVT_AVOPLOT_ELEM_DELETE(self, self.on_delete_element)
        core.EVT_AVOPLOT_ELEM_RENAME(self, self.on_rename_element)        
        
        #register wx event handlers
        self.Bind(aui.EVT_AUINOTEBOOK_PAGE_CLOSE, self.on_tab_close)
        self.Bind(aui.EVT_AUINOTEBOOK_PAGE_CHANGED, self.on_tab_change)

        
        try:
            self.Bind(aui.EVT_AUINOTEBOOK_TAB_RIGHT_DOWN, 
                      self.on_tab_right_click)
        except AttributeError:
            #new version of wx has renamed this for some reason!
            self.Bind(aui.EVT__AUINOTEBOOK_TAB_RIGHT_DOWN, 
                      self.on_tab_right_click)
    
    
    def on_tab_change(self, evnt):
        """
        Event handler for tab change events. Calls on set_selected() on the 
        figure associated with the newly selected tab.
        """
        idx = self.GetSelection()
        fig = self.GetPage(idx)
        fig.set_selected()
    
    
    def on_tab_close(self, evnt):
        """
        Event handler for tab close events. This vetos the event to prevent the
        notebook from destroying the window and then calls delete() on the 
        figure object associated with the tab that has just been closed, relying
        on the event handlers for the AvoPlotElementDelete event to actually
        destroy the window when it is finished with (this is done by 
        on_delete_element() in this class)
        """
        #don't let the notebook actually close the tab, otherwise it will 
        #destroy the window as well
        evnt.Veto() 
        
        idx = self.GetSelection()
        fig = self.GetPage(idx)
        
        #rely on the AVOPLOT_ON_ELEM_DELETE event to destroy the window
        fig.delete() 
        
    
    def on_new_element(self, evnt):
        """
        Event handler for AvoPlotElementAdd events. Adds a page to the notebook
        for newly created figure objects.
        """
        el = evnt.element
        
        #add the element to the mapping
        artists = el.get_mpl_artists()

        for a in artists:
            assert not self.__mplartist_to_element_map.has_key(a), "multiple elements cannot share the same artists"
            self.__mplartist_to_element_map[a] = el
        
        if isinstance(el, figure.AvoPlotFigure):
            el.canvas.mpl_connect('pick_event', self.on_pick)
            self.AddPage(el, el.get_name())
    
    
    def on_pick(self, evnt):
        #because pick events are generated for everything under the click (i.e. data series and subplot etc)
        #on pick needs to store events in a temporary list which then gets parsed by an OnIdle handler.
        
        self.__pick_evnts_to_process.append(evnt)
        avoplot.call_on_idle(self.process_picks)
        
    
    def process_picks(self):   
         
        if not self.__pick_evnts_to_process:
            return
        
        #TODO - the evnt processed should come from the highest level pick event
        #e.g. series should have priority over subplots etc. Does this happen anyway?
        evnt = self.__pick_evnts_to_process.pop()
        self.__pick_evnts_to_process = []
        el = self.__mplartist_to_element_map[evnt.artist]
        
        fig = el
        
        while not isinstance(fig, figure.AvoPlotFigure):
            fig = fig.get_parent_element()
        
        if fig is None or fig._picking_enabled:    
            
            if evnt.mouseevent.button == 1:
                wx.CallAfter(el.set_selected)
            
            elif evnt.mouseevent.button ==3:
                wx.CallAfter(el.on_right_click)
    
    
    def on_select_element(self, evnt):
        """
        Event handler for AvoPlotElementSelect events. Changes the currently
        selected notebook page to that containing the newly selected element.
        
        If the selected element is not a figure, then the figure which contains
        the element is selected.
        
        """
        el = evnt.element
        while not isinstance(el, figure.AvoPlotFigure):
            el = el.get_parent_element()
            if el is None:
                #this should never happen - but just in case
                return

        idx = self.GetPageIndex(el)
        if idx >= 0:
            if idx != self.GetSelection():
                try:
                    self.ChangeSelection(idx) #only available in wx >V2.9.3
                except AttributeError:
                    self.SetSelection(idx)                 
    
    
    def on_delete_element(self, evnt):
        """
        Event handler for AvoPlotElementDelete events. If the element is a figure
        then the notebook page associated with the figure is deleted - note that
        this destroys the window, and so future attempts to access the figure
        object will cause an exception.
        """
        el = evnt.element
        
        #remove the element from the mapping
        artists = el.get_mpl_artists()
        if artists:
            for a in artists:
                self.__mplartist_to_element_map.pop(a)
        
        if isinstance(el, figure.AvoPlotFigure):
            idx = self.GetPageIndex(el)
            if idx >= 0:
                self.RemovePage(idx)
            
            
    def on_rename_element(self, evnt):
        """
        Event handler for AvoPlotElementRename events. If the element is a 
        figure then the relevant notebook page is renamed accordingly.
        """
        el = evnt.element
        if isinstance(el, figure.AvoPlotFigure):
            idx = self.GetPageIndex(el)
            if idx >= 0:
                self.SetPageText(idx, el.get_name())
            
    
    def on_tab_right_click(self, evnt):
        """
        Event handler for right click events on the notebook tabs. Creates
        a popup menu allowing the user to close the tab, split the tab and 
        rename the tab.
        """
        
        #this is a little bit convoluted because you can't use self.GetPage()
        #to get the tab that was clicked on - because it breaks if the 
        #notebook has been split or the tabs have been rearranged
        
        tab_control = evnt.GetEventObject()
        idx = evnt.GetSelection()
        fig = tab_control.GetWindowFromIdx(idx)
        
        fig.set_selected()
        self.PopupMenu(self._tab_menu)
    
    
    def rename_current_figure(self, evnt):
        """
        Event handler for rename events (from the tab right click menu) for 
        notebook pages. Opens a rename dialog and then sets the name of the 
        relevant figure object. Note that this generates an AvoPlotElementRename
        event and the actual renaming of the notebook tab is left up to the event
        handler for this event - on_rename_element()
        """
        idx = self.GetSelection()
        fig = self.GetPage(idx)
        current_name = fig.get_name()
        
        d = wx.TextEntryDialog(self, "Plot name:", "Rename", 
                               defaultValue=current_name)
        
        if d.ShowModal() == wx.ID_OK:
            new_name = d.GetValue()
            if (new_name and not new_name.isspace() and 
                new_name != current_name):
                fig.set_name(str(new_name))


    def split_figure_horiz(self, *args):
        """
        Splits the selected pane horizontally.
        """
        self.Split(self.GetSelection(), wx.RIGHT)
       
        
    def split_figure_vert(self, *args):
        """
        Splits the selected pane vertically.
        """
        self.Split(self.GetSelection(), wx.BOTTOM)    
        
        
    def unsplit_panes(self, *args):
        """
        Unsplits all the panes.
        """
        #need to unbind the tab change handler - otherwise get stuck in an 
        #infinite event loop
        self.Unbind(aui.EVT_AUINOTEBOOK_PAGE_CHANGED)
        
        self.UnSplit()
        
        self.Bind(aui.EVT_AUINOTEBOOK_PAGE_CHANGED, self.on_tab_change)
        
#        
#        self.Freeze()
#
#        # remember the tab now selected
#        nowSelected = self.GetSelection()
#        # select first tab as destination
#        self.SetSelection(0)
#        # iterate all other tabs
#        for idx in xrange(1, self.GetPageCount()):
#            # get win reference
#            win = self.GetPage(idx)
#            # get tab title
#            title = self.GetPageText(idx)
#            # get page bitmap
#            bmp = self.GetPageBitmap(idx)
#            # remove from notebook
#            self.RemovePage(idx)
#            # re-add in the same position so it will tab
#            self.InsertPage(idx, win, title, False, bmp)
#        
#        # restore orignial selected tab
#        self.SetSelection(nowSelected)
#
#        self.Thaw()
#        
#        self.Bind(aui.EVT_AUINOTEBOOK_PAGE_CHANGED, self.on_tab_change)
#        
#        #send a size event to force redraw of window contents - this is only
#        #really needed in windows
#        self.SendSizeEvent()
        
        