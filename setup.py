import sys
import os

try:
    import py2exe
except ImportError:
    print "Error: Missing py2exe package. Use this for windows compilation only."
    sys.exit(1)

from distutils.core import setup

from sdetools import modules
from sdetools.sdelib import commons

options = {
    'py2exe': {
        'includes':[]
    }
}

for mod_name in modules.__all__:
    options['py2exe']['includes'].append('sdetools.modules.%s' % mod_name)

static_files = []
root_path = os.path.split(commons.base_path)[0]
for root, dirnames, filenames in os.walk(commons.media_path):
    if not filenames:
        continue
    static_files.append((root[len(root_path)+1:], [os.path.join(root, fn) for fn in filenames]))

setup(
    name='sde',
    console=['sde.py'],
    description='SD Elements Tools',
    zipfile=None,
    options=options,
    data_files=static_files,
    )
