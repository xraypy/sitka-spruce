import sys
import numpy as np

import h5py
import zarr

import asteval
try:
    import larch
except ImportError:
    larch = None

from pyshortcuts import gformat

COMMONTYPES = (int, float, complex, str, bytes, bool, list, tuple, np.ndarray)

ARRAY_TYPES = ('h5py.Dataset', 'zarr.Array', 'ndarray')
GROUP_TYPES = ('h5py.Group', 'zarr.Group', 'larch.Group')


def cast_int(val):
    return str(int(val))

def cast_complex(val):
    return f'{gformat(val.real)}+{gformat(val.imag)}j'

def dtype2str(dtype):
    """return string casting type for datatype"""
    cast = repr
    if dtype in (bool, int, np.byte, np.bool, np.int32, np.int64):
        cast = cast_int
    elif dtype in (np.complex64, np.complex128):
        cast = cast_complex
    elif dtype in (np.float64, np.float32, np.float16):
        cast = gformat
    return cast


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

def datasize_repr(obj):
    """return string-representation of data size"""
    if (isinstance(obj, h5py.Dataset) or
        isinstance(obj, np.ndarray)):
        nbytes = obj.nbytes
    else:
        nbytes = sys.getsizeof(obj)

    dsize = f'{(nbytes/1024.0):.1f}KB'
    if nbytes > 9.5e8:
        dsize = f'{(nbytes/1073741824.0):.1f}GB'
    elif nbytes > 9.5e5:
        dsize = f'{(nbytes/1048576.0):.1f}MB'
    return dsize

def dim_repr(reductions):
    """return representation of dimension reductions"""
    reps = []
    for idim, use, method, imin, imax in reductions:
        rep = ':'
        if use:
            rep = f'{imin}' if method == 'single' else f'{method}({imin},{imax})'
        reps.append(rep)
    return f"[{','.join(reps)}]"

def get_data(obj, reductions):
    """return dataset (1d or 2d) from multidimensional array"""
    slices = []
    meths = []
    ndims = len(obj.shape)
    for idim, use, method, imin, imax in reductions[:ndims]:
        m = None
        if use:
            if method == 'single':
                slices.append(slice(imin, imin+1))
            else:
                m = method
                slices.append(slice(imin, imax))
        else:
            slices.append(slice(None, None))
        meths.append(m)

    ret = obj[tuple(slices)]
    oshape = ret.shape
    off = 0
    for i, meth  in enumerate(meths):
        if meth in ('sum', 'mean'):
            ret = ret.sum(axis=(i-off))
            off += 1
            if meth == 'mean':
                ret = ret / (1.0*oshape[i])

    return ret.squeeze()


class SitkaData:
    """
    Sitka Datasets and evaluation with asteval

    Attributes
    -----------
    datasets     dict for hdf5/zarr objects
    arrays       dict of working arrays taken from datasets or saved by user
    arrayshapes  dict of arrayshapes to list of named arrays.


    Methods
    -----------
    add_dataset   add dataset by name
    add_array     add an array by name
    eval          evaluate an expreesion or block of code with arrays/datasets
    """
    def __init__(self):
        self.datasets = {}
        self.arrayshapes = {0: []}
        self._asteval = asteval.Interpreter(with_numpy=True,
                                with_import=True, with_importfrom=True)
        self._asteval.symtable['datasets'] = self.datasets
        self.arrays  = {}
        self._last_error = None

    def add_dataset(self, name, dataset):
        self.datasets[name] = dataset

    def add_array(self, name, data):
        """add array to interpreter, and keep track of its shape"""

        # remove existing value
        if name in self.arrays:
            oldval = self.arrays.pop(name)
            dshape = 0
            if isinstance(oldval, np.ndarray):
                dshape = oldval.shape
            # print("add_array ", name, dshape, self.arrayshapes[dshape])
            if name in self.arrayshapes[dshape]:
                self.arrayshapes[dshape].remove(name)

        # add new data array
        dshape = 0
        if isinstance(data, np.ndarray):
            dshape = data.shape
        if dshape not in self.arrayshapes:
            self.arrayshapes[dshape] = []
        self.arrayshapes[dshape].append(name)
        self.arrays[name] = data
        self._asteval.symtable.update(self.arrays)

    def eval(self, str):
        out = self._asteval(str)
        if len(self._asteval.error) > 0:
            self._last_error = [e for e in self._asteval.error]
            return None
        else:
            return out
