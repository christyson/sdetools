# NOTE: Before running ensure that the options are set properly in the
#       configuration file

import sys, os, unittest
sys.path.append(os.path.split(os.path.split(os.path.split(os.path.abspath(__file__))[0])[0])[0])

from alm_integration.tests.alm_plugin_test_helper import AlmPluginTestHelper
from sdelib.conf_mgr import config
from sdelib.interactive_plugin import PlugInExperience
from modules.sync_jira.jira_plugin import JIRAConnector, JIRAAPIBase

CONF_FILE_LOCATION = 'test_settings.conf'

class TestJiraCase(AlmPluginTestHelper, unittest.TestCase):
    def setUp(self):
        config.parse_config_file(CONF_FILE_LOCATION)
        self.tac = JIRAConnector(PlugInExperience(config), JIRAAPIBase(config))
        super(TestJiraCase, self).setUp()

if __name__ == "__main__":
    unittest.main()