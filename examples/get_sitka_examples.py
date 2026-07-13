import time
import sys
import requests
import zipfile

FILENAME = 'sitka_examples.zip'

SOURCE_URLS = ('https://millenia.cars.aps.anl.gov/xraylarch/downloads/',
               'https://docs.xrayabsorption.org/sitka_spruce/')

t0 = time.time()
downloaded = False

for src in SOURCE_URLS:
    url = f"{src:s}/{FILENAME:s}"
    try:
        req = requests.get(url, verify=True, timeout=30)
        downloaded  = (req.status_code == 200)
    except Exception as exc1:
        pass
    if downloaded:
        break

if downloaded:
    with open(FILENAME, 'wb') as fh:
        fh.write(req.content)
    print(f"Downloaded {FILENAME}: {(time.time()-t0):.2f} sec")
    time.sleep(0.25)
    try:
        zfile = zipfile.ZipFile(FILENAME)
    except Exception as exc2:
        print(f"could not open {FILENAME} as a zip file.")
        zfile = None
    if zfile is not None:
        try:
            zfile.extractall()
            print(f"extracted data from {FILENAME}.")
        except Exception:
            print(f"could not extract data from zip file {FILENAME}.")

else:
    print(f"Download of {FILENAME} failed")
