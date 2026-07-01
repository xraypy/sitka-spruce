import numpy as np

from pathlib import Path

import h5py
import zarr

import asteval
try:
    import larch
except ImportException:
    larch = None


COMMONTYPES = (int, float, complex, str, bytes, bool, list, tuple, np.ndarray)

ARRAY_TYPES = ('h5py.Dataset', 'zarr.Array', 'ndarray')
GROUP_TYPES = ('h5py.Group', 'zarr.Group', 'larch.Group')


def get_items(obj):
    """return whether object is dict-like for tree"""
    if (isinstance(obj, dict) or
        (isinstance(obj, h5py.Group)) or
        (larch is not None and isinstance(obj, larch.Group))):
        return {key: val for key, val in obj.items()}
    if isinstance(obj, zarr.Group):
        return {key: obj[key] for key in obj.keys()}
    elif (isinstance(obj, h5py.Dataset) or
          isinstance(obj, zarr.Array)):
        return obj


def get_itemtype(obj):
    """return 'itemtyp for object,

    is dict-like for tree

    """
    itemtype = None
    if isinstance(obj, dict):
        itemtype = 'dict'
    elif larch is not None and isinstance(obj, larch.Group):
        itemtype = 'larch.Group'
    elif isinstance(obj, h5py.Group):
        itemtype = 'h5py.Group'
    elif isinstance(obj, zarr.Group):
        itemtype = 'zarr.Group'
    elif isinstance(obj, h5py.Dataset):
        itemtype = 'h5py.Dataset'
    elif isinstance(obj, zarr.Array):
        itemtype = 'zarr.Array'
    else:
        itemtype = obj.__class__.__name__
    return itemtype

def get_attributes(obj):
    """get attributes for hdf5 Groups/Datasets"""
    out = {}
    if h5py is not None and isinstance(obj, (h5py.Group, h5py.Dataset)):
        if isinstance(obj, h5py.Group):
            out['# members'] = len(obj.keys())
        if isinstance(obj, h5py.Dataset):
            out['dtype'] = str(obj.dtype)
            out['shape'] = obj.shape
            out['chunks'] = obj.chunks
            if obj.compression is not None:
                out['compression'] = obj.compression
            if obj.compression_opts is not None:
                out['compression_opts'] = obj.compression_opts

        if len(obj.attrs) > 0:
            out['_attributes_'] = 'object attibutes'
            for key, val in obj.attrs.items():
                out[key] = val

    for key, val in out.items():
        if isinstance(val, bytes):
            val = val.decode('utf-8')
        elif isinstance(val, (np.int64, np.int32)):
            val = str(int(val))
        elif isinstance(val, (np.float64, np.float32, np.float16)):
            val = str(float(val))
        elif isinstance(val, (np.complex128, np.complex64)):
            val = str(complex(val))
        elif not isinstance(val, str):
            val = repr(val)
        out[key] = val
    return out


def get_data(obj, reductions):
    """return dataset (1d or 2d) from multidimensional array"""
    # print("get data ", obj, obj.shape,  reductions)
    ret = obj[()]
    slices = {}
    for ix in range(len(obj.shape), 0, -1):
        idim = ix - 1
        slices[idim] = ':'
        try:
            jdim, use, method, i0, i1 = reductions[idim]
        except Exception:
            jdim, use, method, i0, i1 = idim, True, 'sum', 0, obj.shape(idim)
        if use:
            if method == 'single':
                ret = ret.take((i0), axis=idim)
                slices[idim] = f'{i0}'
            else:
                ret = ret.take(range(i0, 1+i1), axis=idim).sum(axis=idim)
                if method == 'mean':
                    ret = ret/(1+i1-i0)
                slices[idim] = f'{method}({i0},{i1})'

    s = []
    for key, val in slices.items():
        s.append(val)
    op = '[' + ','.join(reversed(s)) + ']'
    return ret, op

class SitkaData:
    """
    Sitka Datasets and evaluation
    """
    def __init__(self):
        self.datasets = {}
        self.arrayshapes = {0: []}
        self._asteval = asteval.Interpreter(with_numpy=True,
                                with_import=True, with_importfrom=True)
        self._symtab  = self._asteval.symtable
        self._symtab['dsets'] = self.datasets
        self._last_error = None

    def add_dataset(self, name, dataset):
        self.datasets[name] = dataset

    def add_array(self, name, data):
        """add array to interpreter, and keep track of its shape"""

        # remove existing value
        if name in self_symtab:
            oldval = self_symtab.pop(name)
            dshape = 0
            if isinstance(oldval, np.ndarray):
                dshape = oldval.shape
            if name in self.arrayshapes[dshape]:
                self.arrayshapes[dshape].pop(name)

        # add new
        dshape = 0
        if isinstance(data, np.ndarray):
            dshape = data.shape
        if dshape not in self.arrayshapes:
            self.arrayshapes[dshape] = []
        self.arrayshapes[dshape].append(name)
        self._symtab[name] = data


    def eval(self, str):
        out = self._asteval(str)
        if len(self._asteval.error) > 0:
            self._last_error = [e for e in self._asteval.error]
            return None
        else:
            return out
