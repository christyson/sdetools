__all__ = [
    'call',
    'sdelib', 
    'modules', 
    'alm_integration', 
    'extlib',
]

VERSION = '3.0.1'

def setup_path():
    import sys
    import os

    from sdetools.sdelib import commons

    if sys.platform.startswith("win"):
        base_path = os.path.split(os.path.abspath(sys.argv[0]))[0]
        base_path = os.path.join(base_path, 'sdetools')
    else:
        current_file = __file__
        base_path = os.path.split(os.path.abspath(__file__))[0]

    commons.setup_base_path(base_path)

setup_path()

def set_api_connector(api_module):
    from sdetools.sdelib import sdeapi

    sdeapi.APIBase = api_module

def call(cmd_name, options, *args):
    from sdetools.sdelib import mod_mgr

    exit_stat = mod_mgr.run_command(cmd_name, args, 'import', call_options=options)

    return exit_stat