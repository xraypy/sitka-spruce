import time
from threading import Thread
import numpy as np

import wx

from wxmplot import ImageFrame

from wxutils import (GridPanel, SimpleText, pack, Button, HLine,
                     Choice, Check, LEFT, TextCtrl, Popup,
                     get_color, register_darkdetect)

from .gui_utils import get_font, WIN_CHOICES
from .dimreduce import DimReducePanel
from .data import ARRAY_TYPES, get_data, dim_code, datasize_repr

class ArrayImagePanel(wx.Panel):
    """Image Show Config Panel for HDF5/Zarr datasets"""
    def __init__(self, parent, size=(750, 600)):
        wx.Panel.__init__(self, parent, size=size)
        self.parent = parent

        self.SetBackgroundColour(get_color('sbg'))
        self.SetFont(get_font())
        self.data_shape = None
        self.data_obj = None
        self.xsel_cur, self.ysel_cur = -1, -1
        self.skip_dim_proc = False
        self.imageframes = {}
        self.wids = wids = {}


        panel = GridPanel(self, ncols=7, nrows=10, pad=2, itemstyle=LEFT)
        self.dim_reduce = DimReducePanel(parent=panel, callback=self.onDimReduce)

        wids['imshow'] = Button(panel, 'Show Image', size=(200, -1),
                                action=self.onImshow)


        wids['plot_xval'] = Choice(panel, ['<index>'],
                                   size=(200, -1), action=self.onImshow)
        wids['plot_yval'] = Choice(panel, ['<index>'],
                                   size=(200, -1), action=self.onImshow)
        wids['ydir'] = Check(panel, ' ', size=(100, -1), default=False)


        wids['win'] = Choice(panel, WIN_CHOICES, size=(75, -1))
        wids['win'].SetStringSelection('1')

        wids['axes'] =  ['dim0: 0 points', 'dim1: 0 points']

        wids['xdim'] = Choice(panel, wids['axes'],
                              size=(200, -1), action=self.onXdim)
        wids['ydim'] = Choice(panel, wids['axes'],
                              size=(200, -1), action=self.onYdim)
        wids['ydim'].SetSelection(0)
        wids['xdim'].SetSelection(1)


        wids['save_array'] = Button(panel, 'Save Array', size=(125, -1),
                                  action=self.onNameArray)
        wids['array_name'] = TextCtrl(panel, 'imgdat', size=(200, -1),
                                      act_on_losefocus=False,
                                      action=self.onNameArray)
        wids['check_overwrite']  = Check(panel, ' ', size=(30, -1), default=True)

        wids['red_array'] = Choice(panel, ['<none>'], size=(200, -1), action=self.onRGBChoice)
        wids['green_array'] = Choice(panel, ['<none>'], size=(200, -1), action=self.onRGBChoice)
        wids['blue_array'] = Choice(panel, ['<none>'], size=(200, -1), action=self.onRGBChoice)

        wids['red_text'] = SimpleText(panel, ' ', size=(300, -1))
        wids['blue_text'] = SimpleText(panel, ' ', size=(300, -1))
        wids['green_text'] = SimpleText(panel, ' ', size=(300, -1))

        wids['show_rgb'] = Button(panel, 'Show RGB Image', size=(200, -1),
                                  action=self.onShowRGB)


        def padd_text(text, dcol=1, size=(100, -1), newrow=True):
            panel.Add(SimpleText(panel, text, size=size, style=LEFT),
                      dcol=dcol, newrow=newrow)

        padd_text(' Y (Vert): ', newrow=True)
        panel.Add(wids['ydim'])
        padd_text(' Y values: ', newrow=False)
        panel.Add(wids['plot_yval'])

        padd_text(' X (Horiz): ')
        panel.Add(wids['xdim'])
        padd_text(' X values: ', newrow=False)
        panel.Add(wids['plot_xval'])

        padd_text(' ')
        panel.Add(wids['imshow'])
        padd_text(' Window:', newrow=False)
        panel.Add(wids['win'])

        padd_text(' ')
        panel.Add((5, 5))
        padd_text(' Y=0 at top?', size=(125, -1), newrow=False)
        panel.Add(wids['ydir'], dcol=2)


        panel.Add((5, 5), newrow=True)
        panel.Add(self.dim_reduce, dcol=5, newrow=True)
        panel.Add((5, 5), newrow=True)

        panel.Add(wids['save_array'], newrow=True)
        panel.Add(wids['array_name'])
        padd_text(' Verify Overwrite', size=(125, -1), newrow=False)
        panel.Add(wids['check_overwrite'], dcol=1)

        panel.Add((5, 5), newrow=True)
        panel.Add(HLine(panel, size=(725, 3)), dcol=7, newrow=True)
        panel.Add((5, 5), newrow=True)
        panel.Add(wids['show_rgb'], dcol=2, newrow=True)

        padd_text(' Red: ', newrow=True)
        panel.Add(wids['red_array'])
        panel.Add(wids['red_text'], dcol=3)
        padd_text(' Green: ', newrow=True)
        panel.Add(wids['green_array'])
        panel.Add(wids['green_text'], dcol=3)
        padd_text(' Blue: ', newrow=True)
        panel.Add(wids['blue_array'])
        panel.Add(wids['blue_text'], dcol=3)

        panel.pack()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(panel, 1, 0, LEFT|wx.GROW, 4)
        pack(self, sizer)
        register_darkdetect(self.onDarkMode)

    def onDarkMode(self, is_dark=None):
        fgcol = get_color('text', dark=is_dark)
        bgcol = get_color('sbg', dark=is_dark)
        self.SetBackgroundColour(bgcol)
        self.SetForegroundColour(fgcol)
        self.SetBackgroundColour(bgcol)
        self.SetForegroundColour(fgcol)
        wx.CallAfter(self.Refresh)

    def onNameArray(self, event=None):
        arr_name = self.wids['array_name'].GetValue()
        check_overwrite = self.wids['check_overwrite'].IsChecked()
        if check_overwrite and arr_name in self.parent.data.arrays:
            ret = Popup(self, f"Overwrite Array '{arr_name}'?\n",
                        'Verify Overwrite',
                        style=wx.YES_NO|wx.ICON_QUESTION)
            if ret != wx.ID_YES:
                return

        ndim = len(self.data_obj.shape)
        reddim = self.dim_reduce.get_result(ndim)
        _yarr = get_data(self.data_obj, reddim)
        ylabel = dim_code(reddim)
        access_code = f"['{self.filename}']['{self.itemname}']{ylabel}"
        self.parent.data.add_array(arr_name, _yarr, address=access_code)
        wx.CallAfter(self.update_array_choices)


    def onXdim(self, event=None):
        if self.skip_dim_proc:
            return
        self.skip_dim_proc = True
        xsel = self.wids['xdim'].GetSelection()
        ysel = self.wids['ydim'].GetSelection()
        if ysel == xsel and xsel != self.xsel_cur:
            if self.xsel_cur < 0:
                self.xsel_cur = 1 if xsel==0 else 0
            self.wids['ydim'].SetSelection(self.xsel_cur)
            self.ysel_cur = self.xsel_cur
        else:
            self.ysel_cur = ysel
        self.xsel_cur = xsel
        if self.data_shape is not None:
            for i, npts in enumerate(self.data_shape):
                enable = i not in (self.xsel_cur, self.ysel_cur)
                self.dim_reduce.enable_dimension(i, enable=enable, npts=npts)

        self.skip_dim_proc = False
        self.update_array_choices()

    def onYdim(self, event=None):
        if self.skip_dim_proc:
            return
        self.skip_dim_proc = True
        xsel = self.wids['xdim'].GetSelection()
        ysel = self.wids['ydim'].GetSelection()
        if ysel == xsel and ysel != self.ysel_cur:
            if self.ysel_cur < 0:
                self.ysel_cur = 1 if ysel==0 else 0
            self.wids['xdim'].SetSelection(self.ysel_cur)
            self.xsel_cur = self.ysel_cur
        else:
            self.xsel_cur = xsel
        self.ysel_cur = ysel

        if self.data_shape is not None:
            for i, npts in enumerate(self.data_shape):
                enable = i not in (self.xsel_cur, self.ysel_cur)
                self.dim_reduce.enable_dimension(i, enable=enable, npts=npts)

        self.skip_dim_proc = False
        self.update_array_choices()

    def update_array_choices(self, event=None):
        ystr = self.wids['ydim'].GetStringSelection()
        words = ystr.replace('dim', '').replace('points', '').split()
        yshape = (int(words[1]), )

        xstr = self.wids['xdim'].GetStringSelection()
        words = xstr.replace('dim', '').replace('points', '').split()
        xshape = (int(words[1]), )

        xchoices = ['<index>']
        xchoices.extend(self.parent.data.array_shapes.get(xshape, []))

        ychoices = ['<index>']
        ychoices.extend(self.parent.data.array_shapes.get(yshape, []))
        self.wids['plot_xval'].SetChoices(xchoices)
        self.wids['plot_yval'].SetChoices(ychoices)

        rgb_choices = ['<none>']
        cval = {'red': '<none>', 'blue': '<none>', 'green': '<none>'}
        for col in ('red', 'green', 'blue'):
            cval[col] = self.wids[f'{col}_array'].GetStringSelection()

        cshape = None
        for col in ('red', 'green', 'blue'):
            val = cval[col]
            if val in self.parent.data.arrays:
                cshape = self.parent.data.arrays[val].shape
        if cshape is None:
            rgb_choices.extend(self.parent.data.arrays.keys())
        else:
            rgb_choices.extend(self.parent.data.array_shapes.get(cshape, []))

        self.wids['red_array'].SetChoices(rgb_choices)
        self.wids['green_array'].SetChoices(rgb_choices)
        self.wids['blue_array'].SetChoices(rgb_choices)

        for col in ('red', 'green', 'blue'):
            if cval[col] in rgb_choices:
                self.wids[f'{col}_array'].SetStringSelection(cval[col])
                self.wids[f'{col}_text'].SetLabel(str(cshape))

    def onRGBChoice(self, event=None):
        self.update_array_choices()

    def set_object(self, object, itemtype='?', itemname='', filename='', **kws):
        """fill from object"""
        self.filename = filename
        self.itemname = itemname
        self.data_obj = object
        # print(f'Plot2D  {filename=}, {itemname=} {itemtype=}')
        if (itemtype in ARRAY_TYPES):
            self.data_shape = object.shape
            choices = self.dim_reduce.set_datashape(object.shape)
            if len(choices) > 0:
                xcur = self.wids['xdim'].GetSelection()
                ycur = self.wids['ydim'].GetSelection()
                self.wids['xdim'].SetChoices(choices)
                self.wids['ydim'].SetChoices(choices)
                # might be overkill repetitive:
                if xcur >= len(self.data_shape):
                    xcur = 0
                if ycur >= len(self.data_shape):
                    ycur = 0
                if xcur > len(self.data_shape):
                    xcur = 0
                if ycur > len(self.data_shape):
                    ycur = 0
                if xcur == ycur:
                    ycur = (ycur - 1) % len(self.data_shape)
                if self.data_shape[xcur] < 2:
                    xcur = (xcur - 1) % len(self.data_shape)
                if self.data_shape[ycur] < 2:
                    ycur = (ycur - 1) % len(self.data_shape)
                if xcur == ycur:
                    ycur = (ycur - 1) % len(self.data_shape)

                self.wids['xdim'].SetSelection(xcur)
                self.wids['ydim'].SetSelection(ycur)

                self.dim_reduce.enable_dimension(xcur, enable=False, npts=None)
                self.dim_reduce.enable_dimension(ycur, enable=False, npts=None)

                xcur = self.wids['xdim'].GetSelection()
                ycur = self.wids['ydim'].GetSelection()
        self.Refresh()


    def show_imageframe(self, window=1, **opts):
        shown = False
        if window in self.imageframes:
            try:
                self.imageframes[window].Raise()
                shown = True
            except Exception:
                f = self.imageframes.pop(window)
                del f
                shown = False
        if not shown:
            self.imageframes[window] = ImageFrame(self, **opts)
            self.imageframes[window].Raise()
        return self.imageframes[window]

    def onDimReduce(self, event=None, dim=None, reduce=None):
        self.onImshow(new=True)


    def onImshow(self, event=None, new=True):
        win   = self.wids['win'].GetStringSelection()
        ydir  = self.wids['ydir'].IsChecked()
        ydim  = self.wids['ydim'].GetSelection()
        xdim  = self.wids['xdim'].GetSelection()
        xstr  = self.wids['plot_xval'].GetStringSelection()
        ystr  = self.wids['plot_yval'].GetStringSelection()

        ndim = len(self.data_obj.shape)
        reddim = self.dim_reduce.get_result(ndim)

        def _get_data(reddim):
            self._img = get_data(self.data_obj, reddim)

        data_thread = Thread(target=_get_data, args=(reddim,))
        t0_data = time.time()
        self.parent.status_message('fetching data....')

        data_thread.start()
        time.sleep(0.0005)
        frame_opts = {'title':  f'SitkaImage {win} '}
        iframe = self.show_imageframe(int(win), **frame_opts)

        dlabel = dim_code(reddim)
        self.parent.access_code = f"['{self.filename}']['{self.itemname}']{dlabel}"
        opts = {'title': f'{self.filename} {dlabel}', 'contrast_level':'0.05',
                'colormap': 'viridis'}

        data_thread.join()
        if self._img.dtype == np.bool:
            self._img = self._img.astype(int)

        dt_data = time.time()-t0_data
        dsize = datasize_repr(self._img)
        osize = datasize_repr(self.data_obj)

        self.parent.status_message(f'got data ({dsize} of {osize}) in {dt_data:.2f} seconds')

        if len(self._img.shape) < 2:
            self._img.shape = (self._img.shape[0], 1)

        if (ydim > xdim):
            self._img = self._img.transpose()

        xvals = self.parent.data.arrays.get(xstr, None)
        yvals = self.parent.data.arrays.get(ystr, None)
        if xstr == '<index>' or xvals is None:
            xvals = np.arange(self._img.shape[1])
        if ystr == '<index>' or yvals is None:
            yvals = np.arange(self._img.shape[0])

        if ydir:
            self._img = self._img[::-1, :]
            yvals = yvals[::-1]

        iframe.display(self._img, x=xvals, y=yvals, **opts)
        iframe.Show()
        iframe.Raise()
        self.parent.data.add_array('_imgdat', self._img, address=self.parent.access_code)

    def onShowRGB(self, event=None):
        """Display three arrays combined as RGB channels"""
        win = self.wids['win'].GetStringSelection()
        red_name = self.wids['red_array'].GetStringSelection()
        green_name = self.wids['green_array'].GetStringSelection()
        blue_name = self.wids['blue_array'].GetStringSelection()

        if red_name == '<none>' and green_name == '<none>' and blue_name == '<none>':
            Popup(self, 'Please select at least one channel for RGB display',
                  'RGB Display Error')
            return

        arrays = self.parent.data.arrays
        channels = {}

        if red_name != '<none>' and red_name in arrays:
            channels['red'] = arrays[red_name]
        if green_name != '<none>' and green_name in arrays:
            channels['green'] = arrays[green_name]
        if blue_name != '<none>' and blue_name in arrays:
            channels['blue'] = arrays[blue_name]

        if len(channels) == 0:
            Popup(self, 'Selected arrays not found', 'RGB Display Error')
            return

        self.parent.status_message('Combining RGB channels...')

        try:
            rgb_img = self.make_rgb(channels)
            if rgb_img is None:
                return

            frame_opts = {'title': f'SitkaRGB Image {win} '}
            iframe = self.show_imageframe(int(win), **frame_opts)

            title_parts = [self.filename]
            if red_name != '<none>':
                title_parts.append(f'R:{red_name}')
            if green_name != '<none>':
                title_parts.append(f'G:{green_name}')
            if blue_name != '<none>':
                title_parts.append(f'B:{blue_name}')

            opts = {'title': ' '.join(title_parts)}
            iframe.display(rgb_img, **opts)
            iframe.Show()
            iframe.Raise()

            self.parent.data.add_array('_rgb_imgdat', rgb_img,
                                      address='[RGB]')
            self.parent.status_message('RGB image displayed successfully')

        except Exception as e:
            Popup(self, f'Error combining RGB channels:\n{str(e)}',
                  'RGB Display Error')
            self.parent.status_message(f'RGB display error: {str(e)}')

    def make_rgb(self, channels):
        """Combine selected channels into an RGB image

        Parameters
        ----------
        channels : dict
            Dictionary with keys 'red', 'green', 'blue' and 2D numpy array values

        Returns
        -------
        rgb_img : ndarray
            Shape (height, width, 3) RGB image, normalized to 0-255 range
        """
        if not channels:
            return None

        shapes = [arr.shape for arr in channels.values()]
        if len(set(shapes)) > 1:
            Popup(self, 'All selected channels must have the same shape',
                  'Shape Mismatch Error')
            return None

        shape = shapes[0]
        if len(shape) != 2:
            Popup(self, 'All channels must be 2D arrays',
                  'Dimension Error')
            return None

        rgb_img = np.zeros(shape + (3,), dtype=np.uint8)

        channel_order = [('red', 0), ('green', 1), ('blue', 2)]
        for channel_name, channel_idx in channel_order:
            if channel_name in channels:
                channel_data = channels[channel_name].astype(np.float32)
                channel_min = channel_data.min()
                channel_max = channel_data.max()
                if channel_max > channel_min:
                    channel_data = (channel_data - channel_min) / (channel_max - channel_min) * 255
                else:
                    channel_data[:] = 127
                rgb_img[:, :, channel_idx] = channel_data.astype(np.uint8)

        return rgb_img
