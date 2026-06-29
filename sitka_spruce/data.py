import numpy as np

from pathlib import Path

import h5py

try:
    import zarr
except:
    zarr = None

try:
    import larch
except:
    larch = None


def get_items(obj):
    """return if object is dict-like for tree"""
    if (isinstance(obj, dict) or
        (larch is not None and isinstance(obj, larch.Group)) or
        (h5py is not None and isinstance(obj, h5py.Group))):
        return {key: val for key, val in obj.items()}
    if (zarr is not None and isinstance(obj, zarr.Group)):
        return {key: obj[key] for key in obj.keys()}
    elif ((h5py is not None and isinstance(obj, h5py.Dataset)) or
          (zarr is not None and isinstance(obj, zarr.Array))):
        return obj


def get_itemtype(obj):
    """return if object is dict-like for tree"""
    itemtype = None
    if isinstance(obj, dict):
        itemtype = 'dict'
    elif larch is not None and isinstance(obj, larch.Group):
        itemtype = 'larch.Group'
    elif h5py is not None and isinstance(obj, h5py.Group):
        itemtype = 'h5py.Group'
    elif zarr is not None and isinstance(obj, zarr.Group):
        itemtype = 'zarr.Group'
    elif h5py is not None and isinstance(obj, h5py.Dataset):
        itemtype = 'h5py.Dataset'
    elif zarr is not None and isinstance(obj, zarr.Array):
        itemtype = 'zarr.Array'
    elif isinstance(obj, np.ndarray):
        itemtype = 'np.ndarray'
    elif isinstance(obj, COMMONTYPES):
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

def get_data1d(obj, dim0, reductions):
    """return 1d dataset from multidimensional array"""
    # print("get data1d ", obj, obj.shape, dim0, reductions)
    ret = obj[()]
    slices = {}
    for ix in range(len(obj.shape), 0, -1):
        idim = ix - 1
        slices[idim] = ':'
        try:
            jdim, use, method, i0, i1 = reductions[idim]
        except IndexError:
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



def get_data2d(obj, dim0, dim1, reductions):
    """return 2d dataset from multidimensional array"""
    ret = obj[()]
    slices = {}
    for ix in range(len(obj.shape), 0, -1):
        idim = ix - 1
        slices[idim] = ':'
        try:
            jdim, use, method, i0, i1 = reductions[idim]
        except IndexError:
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
