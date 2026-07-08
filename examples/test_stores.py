import numpy as np
import zarr
from zarr_sqlite import SQLiteStore

import matplotlib.pyplot as plt
try:
    from wxmplot.interactive import imshow
except:
    imshow = None

def create_zarr_example(store_name, constructor, win=1):
    print(f"{store_name=}   {constructor=}")

    sopts = {'read_only': False}
    if constructor == zarr.storage.ZipStore:
        sopts['mode'] = 'a'

    root = zarr.open(store=constructor(store_name, **sopts), mode='a')
    group1 = root.create_group('group1')

    i = np.arange(30000)/60.0
    x = i + np.random.normal(size=len(i), scale=1.5)
    y = np.sin(x/13) + 0.7*np.cos(x/47) + np.random.normal(size=len(i), scale=0.05)
    x.shape = (150, 200)
    y.shape = (150, 200)

    group1.create_array(data=x, name='xdat')
    group1.create_array(data=y, name='ydat')

    print(group1, list(group1.keys()))

    ##
    read_root = zarr.open(store=store_name)
    ytest = read_root['group1/ydat'][()]

    print(f"## DONE {read_root=}")
    if imshow:
        imshow(ytest, win=win)
    else:
        plt.imshow(ytest)
        plt.show()

##############
storages = {'z1.zarr':  zarr.storage.LocalStore,
            'z1.zip':  zarr.storage.ZipStore,
            # 'z1.db':  SQLiteStore,
            }

win = 0
for sname, constructor in storages.items():
    win += 1
    create_zarr_example(sname, constructor, win=win)
