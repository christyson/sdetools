from sdelib.cmd import BaseCommand
from modules.sync_mingle.mingle_plugin import MingleConnector, MingleAPIBase
from alm_integration.alm_plugin_base import AlmException
from sdelib.interactive_plugin import PluginError


class Command(BaseCommand):
    help = 'Mingle <-> SDE sync utility.'

    def configure(self):
        mbase = MingleAPIBase(self.config)
        self.mingle = MingleConnector(self.config, mbase)

    def handle(self):
        self.mingle.initialize()
        self.mingle.synchronize()
        return True
