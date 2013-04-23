import xml.parsers.expat
import socket

from sdetools.extlib import SOAPpy

from sdetools.alm_integration.alm_plugin_base import AlmException
from sdetools.modules.sync_jira.jira_shared import JIRATask

from sdetools.sdelib import log_mgr
logger = log_mgr.mods.add_mod(__name__)

class SOAPProxyWrap:
    """
    This is a wrapper for proxy calls so that we don't repeat the exception handling code everywhere
    """
    class __FCall:
        def __init__(self, fobj, fname):
            self.__fobj = fobj
            self.__fname = fname

        def __call__(self, *args):
            logger.info('Calling JIRA SOAP method %s' % self.__fname)
            logger.debug(' + Args: %s' % ((repr(args)[:200]) + (repr(args)[200:] and '...')))
            try:
                return self.__fobj(*args)
            except (xml.parsers.expat.ExpatError, socket.error), err:
                raise AlmException('Unable to access JIRA (for %s). '
                        ' Please check network connectivity.' % (self.fname))

    def __init__(self, proxy):
        self.proxy = proxy

    def __getattr__(self, name):
        f = getattr(self.proxy, name)
        return self.__FCall(f, name)

class JIRASoapAPI:
    def __init__(self, config):
        self.config = config
        self.statuses = None
        self.priorities = None
        self.auth = None
        self.versions = None

    def connect(self):
        config = SOAPpy.Config
        if __name__ in self.config['debug_mods']:
            config.debug = 1

        # Get a proxy to the server
        try:
            proxy = SOAPpy.WSDL.Proxy('%s://%s/rpc/soap/jirasoapservice-v2?wsdl' %
                    (self.config['alm_method'], self.config['alm_server']), config=config)
        except (SOAPpy.Types.faultType, xml.parsers.expat.ExpatError, socket.error), err:
            raise AlmException('Unable to connect to JIRA. Please check server URL. Reason: %s' % (err))
        self.proxy = SOAPProxyWrap(proxy)

        # Attempt to login
        try:
            self.auth = self.proxy.login(self.config['alm_user'], self.config['alm_pass'])
        except SOAPpy.Types.faultType:
            raise AlmException('Unable to login to JIRA. Please check ID, password')

        # Test for project existence
        try:
            result = self.proxy.getProjectByKey(self.auth, self.config['alm_project'])
        except SOAPpy.Types.faultType:
            raise AlmException('Unable to connect to project %s. Please check project'
                               ' settings' % (self.config['alm_project']))
        
        # For JIRA 4 we need the ID-Name mapping for status and priority
        self.statuses = self.proxy.getStatuses(self.auth)
        self.priorities = self.proxy.getPriorities(self.auth)
        self.versions = self.proxy.getVersions(self.auth, self.config['alm_project'])

    def get_version(self, version_name):
        for v in self.versions:
            if v['name']==version_name:
                return v
        return None
 
    def get_issue_types(self):
        try:
            return self.proxy.getIssueTypes(self.auth)
        except SOAPpy.Types.faultType:
            raise AlmException('Unable to get issuetype from JIRA')

    def get_task(self, task, task_id):
        try:
            jql = "project='%s' AND summary~'%s'" % (self.config['alm_project'], task_id)
            issues = self.proxy.getIssuesFromJqlSearch(self.auth, jql, SOAPpy.Types.intType(1))
        except SOAPpy.Types.faultType:
            raise AlmException("Unable to get task %s from JIRA" % task_id)

        # We can't simplify this since issues is a complex object
        if not issues or len(issues) == 0:
            #No result was found from query
            return None

        #We will use the first result from the query
        jtask = issues[0]

        task_resolution = None
        task_status = None
        task_priority = None
        task_versions = []

        if 'resolution' in jtask and jtask['resolution']:
            task_resolution = jtask['resolution']
        if jtask['status']:
            for status in self.statuses:
                if status['id'] == jtask['status']:
                    task_status = status['name']
                    break
        if jtask['priority']:
            for priority in self.priorities:
                if priority['id'] == jtask['priority']:
                    task_priority = priority['name']
                    break
        if jtask['affectsVersions']:
            for version in jtask['affectsVersions']:
                task_versions.append(version['name'])


        return JIRATask(task['id'],
                        jtask['key'],
                        task_priority,
                        task_status,
                        task_resolution,
                        jtask['updated'],
                        self.config['jira_done_statuses'],
                        task_versions)

    def set_version(self, task, version):
        # For SOAP, we must assign all versions (including the new one) to the task
        task.versions.append(version)

        affected_versions = []
        for version_name in task.versions:
            jira_version = self.get_version(version_name)
            if jira_version:
                affected_versions.append(jira_version['id'])
            else:
                raise AlmException("Version %s could not be found in JIRA. '\
                        'Check your sync settings or add the version to JIRA" % version_name)

        try:
            update = [{'id':'versions', 'values':affected_versions}]
            self.proxy.updateIssue(self.auth, task.get_alm_id(), update)
        except (SOAPpy.Types.faultType, AlmException), err:
            raise AlmException('Unable to update issue %s with new version %s' % (task.get_alm_id(), version))
    
        return True

    def add_task(self, task, issue_type_id):
        #Add task
        selected_priority = None
        for priority in self.priorities:
            if priority['name'] == task['alm_priority']:
                selected_priority = priority['id']
                break
        if not selected_priority:
            raise AlmException('Unable to find priority %s' % task['alm_priority'])

        updates = []
        updates.append({'id':'labels', 'values':['SD-Elements']})
        if self.config['alm_project_version']:
            version = self.get_version(self.config['alm_project_version'])
            if version:
                updates.append({'id':'versions', 'values':[version['id']]})
        args = {
            'project': self.config['alm_project'],
            'summary': task['title'],
            'description': task['formatted_content'],
            'priority': selected_priority,
            'type': issue_type_id
        }

        try:
            ref = self.proxy.createIssue(self.auth, args)
            self.proxy.updateIssue(self.auth, ref['key'], updates)
            return ref
        except (SOAPpy.Types.faultType, AlmException), err:
            raise AlmException('Unable to add issue to JIRA')

    def get_available_transitions(self, task_id):
        transitions = self.proxy.getAvailableActions(self.auth, task_id)
        ret_trans = {}
        for transition in transitions:
            ret_trans[transition['name']] = transition['id']
        return ret_trans

    def update_task_status(self, task_id, status_id):
        try:
            self.proxy.progressWorkflowAction(self.auth, task_id, status_id)                
        except SOAPpy.Types.faultType, err:
            logger.error(err)
            raise AlmException("Unable to set task status: %s" % err)
