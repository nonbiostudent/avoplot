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
from matplotlib.patches import Rectangle
import wx

class RectRegionSelect:

    def __init__(self, fig, callback=None):
        """
        Tool to allow a rectangular selection of a figure to be made
        """
        self.figure = fig
        
        self.callback = callback
        self.mpl_fig = fig.get_mpl_figure()
        
        #TODO - select a colour that will be visible against any background
        self.rect_colour = (0, 0, 0)

        self.current_selection = []
        self.cids=[]

        self.rect = None

        self.background = None
        self.press_x = None
        self.press_y = None       
        
        
    def enable_selection(self):
        self.ax = self.mpl_fig.add_axes([0,0,1,1])
        self.ax.xaxis.set_visible(False)
        self.ax.yaxis.set_visible(False)
        self.ax.patch.set_alpha(0)
        
        self.visible = True
        
        #register the event handlers
        self.canvas = self.mpl_fig.canvas
        self.cids.append(self.canvas.mpl_connect('motion_notify_event', self.on_move))
        self.cids.append(self.canvas.mpl_connect('button_press_event', self.on_click))
        self.cids.append(self.canvas.mpl_connect('button_release_event', self.on_release))
        self.cids.append(self.canvas.mpl_connect('draw_event', self.on_draw))
        
        cursor = wx.StockCursor(wx.CURSOR_CROSS)
        self.mpl_fig.canvas.SetCursor(cursor)
        
        #disable the pan and zoom controls
        self.figure.enable_pan_and_zoom_tools(False)
        self.canvas.draw()
        

    def disable_selection(self):
        """
        Disables the selection tool - disconnecting the matplotlib canvas 
        callbacks and clearing any current selection.
        """
        for cid in self.cids:
                self.canvas.mpl_disconnect(cid)
        self.cids = []
        self.visible = False
        
        cursor = wx.StockCursor(wx.CURSOR_DEFAULT)
        self.mpl_fig.canvas.SetCursor(cursor)
        
        #remove any current selection
        self.clear_selection()
        
        #since the on_draw callback is now diasbled - need to clear the 
        #background cache
        self.background = None
        
        self.mpl_fig.delaxes(self.ax)
        self.figure.update()

        
    def on_draw(self, evnt):
        """
        Callback handler for draw events. Re-caches the background for future 
        blitting and redraws the selection rectangles.
        """
        self.update_background()
        self.update()
            
    
    def update_background(self):
        """
        Re-caches the backgound.
        """
        self.background = self.canvas.copy_from_bbox(self.ax.bbox)


    def ignore(self, event):
        'Returns True if event should be ignored, false otherwise'
        return  (self.figure.is_zoomed() or
                 self.figure.is_panned() or
                 not self.visible)


    def on_click(self, event):
        """
        Callback handler for mouse click events in the axis. Creates a new
        selection rectangle.
        """
        if self.ignore(event) or event.button !=1: 
            return
        
        self.buttonDown = True
        
        if not event.guiEvent.ControlDown() and self.current_selection:
            self.clear_selection()
        
        if self.background is None:
            self.update_background()
        
        self.press_x = event.xdata
        self.press_y = event.ydata
        
        w,h, = 0,1
        trans = self.mpl_fig.transFigure 
            
        self.rect= Rectangle((0,0), w, h,
                            transform=trans,
                            visible=False,
                            facecolor=self.rect_colour,
                            alpha=0.35,
                            animated=True
                            )
        
        self.ax.add_patch(self.rect)   


    def clear_selection(self):
        """
        Clear the current selection
        """
        if self.rect is not None:
            self.rect.remove()
            
        self.rect = None
        self.update()
        
        self.current_selection = []
    
    
    def on_release(self, event):
        """
        Event handler for mouse click release events.
        """
        if self.press_x is None or self.ignore(event) or event.button !=1:
            return
        
        self.buttonDown = False

        xmin = self.press_x
        ymin = self.press_y    
        xmax = event.xdata or self.prev[0]
        ymax = event.ydata or self.prev[1]

        xmin,xmax = sorted([xmin, xmax])
        ymin,ymax = sorted([ymin, ymax])
        
        self.current_selection = (xmin, ymin, xmax, ymax)

        self.press_x = None
        self.press_y = None
        
        if self.callback is not None:
            self.callback(self.current_selection)


    def update(self):
        """
        Redraws the selection rectangles.
        """
        if self.background is not None:
            self.canvas.restore_region(self.background)
        
        if self.rect is not None:
            self.ax.draw_artist(self.rect)
            
        self.canvas.blit(self.ax.bbox)


    def on_move(self, event):
        """
        Event handler for mouse move events.
        """
        if self.ignore(event) or self.rect is None:
            return
        
        if None in (event.xdata, event.ydata):
            return 
        
        if self.background is None:
            self.update_background()    
        
        x, y = event.xdata, event.ydata
        self.prev = x, y
        

        if self.press_x is None:
            #if the button is not pressed then nothing else to do
            self.update()
            return
        
        min_x, max_x = sorted([x,self.press_x])
        min_y, max_y = sorted([y, self.press_y])

        cur_rect = self.rect
        self.rect.set_visible(True)
        
        self.rect.set_x(min_x)
        self.rect.set_width(max_x-min_x)
        self.rect.set_y(min_y)
        self.rect.set_height(max_y-min_y)

        self.update()
