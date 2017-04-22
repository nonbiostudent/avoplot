import column_selector
import loader
import wx
filename = "/home/nialp/Desktop/test_data"
filename = '/home/nialp/Desktop/scan1/Processed/20120208/8feb_scan1_wangle.txt'
contents = loader.load_file(filename)
app = wx.PySimpleApp()

c  = column_selector.ColumnSelectorFrame(None, contents)
app.MainLoop()
