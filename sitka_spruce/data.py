import os
import sys
import numpy as np

import hdf5plugin
import h5py
import zarr

import asteval

from pyshortcuts import gformat, isotime
from pathlib import Path

try:
    import larch
except ImportError:
    larch = None


FILE_OPENERS = {'hdf5': h5py.File, 'h5': h5py.File, 'zarr': zarr.open}

COMMONTYPES = (int, float, complex, str, bytes, bool, list, tuple, np.ndarray)

ARRAY_TYPES = ('h5py.Dataset', 'zarr.Array', 'ndarray')
GROUP_TYPES = ('h5py.Group', 'zarr.Group', 'larch.Group')

# reverse map of hdf5plugin filters
HDF_FILTERS_MAP = {v: k for k, v in hdf5plugin.FILTERS.items()}


def get_opener(path):
    """get file opener for path name
    currently returns one of h5py.File or zarr.open
    """
    if isinstance(path, str):
        path = Path(path)

    opener = None
    if path.suffix in FILE_OPENERS:
        opener = FILE_OPENERS[path.suffix]
    elif h5py.is_hdf5(path):
        opener = FILE_OPENERS['h5']
    elif (path.exists() and path.is_dir() and   # home-built 'is_zarr'
          (path/'zarr.json').exists() and
          (path/'zarr.json').is_file()):
        opener = FILE_OPENERS['zarr']
    return opener

def get_sitka_files(folder=None):
    """get sitka supported files from a foloder"""
    files = {}
    if folder is not None:
        path = Path(folder)
        if path.exists and path.is_dir():
            for fname in os.listdir(path):
                thispath = Path(path, fname)
                opener = get_opener(thispath)
                if opener is not None:
                    try:
                        dset = opener(thispath.absolute(), mode='r')
                        files[thispath.name] = dset
                    except Exception:
                        print(f"Warning: could not open {fname} with {opener}")
    return files


def cast_int(val):
    return str(int(val))

def cast_complex(val):
    try:
        out = f'{gformat(val.real)}+{gformat(val.imag)}j'
    except Exception:
        out = f'{val.real}+{val.imag}j'
    return out

def cast_float(val):
    try:
        out = gformat(val)
    except Exception:
        out = f'{val}'
    return out

def cast_bytes(val):
    if isinstance(val, bytes):
        try:
            v = val.decode('utf-8')
        except ValueError:
            v = str(val)
    else:
        v = str(val)
    return v

def dtype2str(dtype):
    """return string casting type for datatype"""
    cast = cast_bytes
    if dtype in (bool, int, np.byte, np.bool, np.uint16, np.uint32,
                 np.uint64, np.int16, np.int32, np.int64):
        cast = cast_int
    elif dtype in (np.complex64, np.complex128):
        cast = cast_complex
    elif dtype in (np.float64, np.float32, np.float16):
        cast = cast_float
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

def get_hdf5_compression_info(obj):
    """get a dict of compression information for a dataset"""
    out = {}
    if obj.compression is not None:
        if obj.compression == 'unknown':  # try to use hdf5plugin to get compression

            plist = obj.id.get_create_plist()
            filters = [plist.get_filter(i) for i in range(plist.get_nfilters())]
            comps, opts = [], []
            for filtid, _, fopts, labbytes in filters:
                try:
                    label = labbytes.decode('utf-8').split(';')[0]
                except Exception:
                    label = None
                if label is None and filtid in HDF_FILTERS_MAP:
                    label = HDF_FILTERS_MAP[filtid]
                comps.append(label)
                opts.append(repr(fopts))

            if len(comps) == 0:
                comps = ['unknown']
            out['compression'] = ', '.join(comps)
            out['compression_opts'] = ', '.join(opts)

        else:
            out['compression'] = obj.compression
            if obj.compression_opts is not None:
                out['compression_opts'] = obj.compression_opts
    return out

def get_attributes(obj, itemname):
    """get attributes for hdf5 Groups/Datasets"""
    out = {}
    if isinstance(obj, (h5py.Group, h5py.Dataset)):
        nodes = [itemname]
        if '/' in itemname:
            nodes = itemname.split('/')
        node = nodes.pop()
        parent = '/'.join(nodes)
        if len(nodes) > 1:
            out['parent'] = parent
        out['node'] = node
        if isinstance(obj, h5py.Group):
            out['# members'] = len(obj.keys())
        elif isinstance(obj, h5py.Dataset):
            if obj.shape == (1, ):
                out['value'] = dtype2str(obj.dtype)(obj[0])
            out['dtype'] = str(obj.dtype)
            out['shape'] = obj.shape
            out['chunks'] = obj.chunks
            out.update(get_hdf5_compression_info(obj))

        if len(obj.attrs) > 0:
            out['_attributes_'] = 'object attibutes'
            for key, val in obj.attrs.items():
                out[key] = val

    for key, val in out.items():
        out[key] = dtype2str(type(val))(val)
    return out
#
#         if isinstance(val, bytes):
#             val = val.decode('utf-8')
#         elif isinstance(val, (np.int64, np.int32, np.int16,
#                               np.uint64, np.uint32, np.uint16)):
#             val = str(int(val))
#         elif isinstance(val, (np.float64, np.float32, np.float16)):
#             val = str(float(val))
#         elif isinstance(val, (np.complex128, np.complex64)):
#             val = str(complex(val))
#         elif not isinstance(val, str):
#             val = repr(val)
#         out[key] = val



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

def dim_code(reductions):
    """return Python code representation of dimension reductions"""
    reps = []
    sums = []
    saxis = []
    off = 0
    npts = 1.0
    for idim, use, method, imin, imax in reductions:
        if not use:
            reps.append(':')
        elif method == 'single':
            reps.append(f'{imin}')
        else:
            reps.append(f'{imin}:{imax}')
            saxis.append(idim)
            sums.append(f'sum(axis={idim-off})')
            off += 1
            if method == 'mean' and imax > (imin+1):
                npts *= (imax-imin)
    words = [f"[{','.join(reps)}]"]
    if len(saxis) == 1:
        words.append(f'sum(axis={saxis[0]})')
    elif len(saxis) > 1:
        words.append(f'sum(axis={tuple(saxis)})')
    out = '.'.join(words)
    if npts > 1.0:
        out = f'{out}/{npts:.1f}'
    return out

def get_data(obj, reductions):
    """return dataset (1d or 2d) from multidimensional array"""
    slices = []
    sumaxis = []
    npts = 1.0
    ndims = len(obj.shape)
    for idim, use, method, imin, imax in reductions[:ndims]:
        if use:
            if method == 'single':
                slices.append(slice(imin, imin+1))
            else:
                slices.append(slice(imin, imax))
                sumaxis.append(idim)
                npts = npts*(imax-imin)
        else:
            slices.append(slice(None, None))

    ret = obj[tuple(slices)]
    if len(sumaxis):
        ret = ret.sum(axis=tuple(sumaxis))/npts
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
        self.arrays  = {}
        self.array_addrs  = {}
        self.array_shapes = {0: []}
        self._asteval = asteval.Interpreter(with_numpy=True,
                                with_import=True, with_importfrom=True)
        self._asteval.symtable['datasets'] = self.datasets
        self._last_error = None

    def add_dataset(self, name, dataset):
        self.datasets[name] = dataset

    def add_array(self, name, data, address=None):
        """add array to interpreter, and keep track of its shape"""
        # print("Add array ", name, data, address)
        # remove existing value
        if name in self.arrays:
            oldval = self.arrays.pop(name)
            dshape = 0
            if isinstance(oldval, np.ndarray):
                dshape = oldval.shape
            # print("add_array ", name, dshape, self.array_shapes[dshape])
            if name in self.array_shapes[dshape]:
                self.array_shapes[dshape].remove(name)

        # add new data array
        dshape = 0
        if isinstance(data, np.ndarray):
            dshape = data.shape
        if dshape not in self.array_shapes:
            self.array_shapes[dshape] = []
        self.array_shapes[dshape].append(name)
        self.arrays[name] = data
        self._asteval.symtable.update(self.arrays)
        if address is not None:
            self.array_addrs[name] = address

    def eval(self, str):
        out = self._asteval(str)
        if len(self._asteval.error) > 0:
            self._last_error = [e for e in self._asteval.error]
            return None
        else:
            return out

    def export_hdf5(self, path, arraynames):
        """write HDF5 file with values for named arrays"""
        f = h5py.File(path, 'a')
        root = f.create_group('sitka_arrays')
        root.attrs['saved_date'] = isotime()
        for name in arraynames:
            dat = self.arrays.get(name, None)
            if dat is None:
                continue
            shape = dat.shape
            dset = root.create_dataset(name,  data=dat,
                                       compression='gzip',
                                       compression_opts=2,
                                       chunks=shape)
            dset.attrs['origin'] = self.array_addrs.get(name, 'unknown')
