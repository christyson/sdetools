# Copyright SDElements Inc
# Extensible two way integration with GitHub

import re
from datetime import datetime

from sdetools.extlib import http_req
from sdetools.sdelib.commons import urlencode_str
from sdetools.sdelib.restclient import RESTBase
from sdetools.sdelib.restclient import URLRequest, APIError
from sdetools.alm_integration.alm_plugin_base import AlmTask, AlmConnector
from sdetools.alm_integration.alm_plugin_base import AlmException

from sdetools.sdelib import log_mgr
logger = log_mgr.mods.add_mod(__name__)

RE_MAP_RANGE_KEY = re.compile('^\d+(-\d+)?$')
GITHUB_DEFAULT_PRIORITY_MAP = {
    '7-10': 'High',
    '4-6': 'Medium',
    '1-3': 'Low',
    }

class GitHubAPI(RESTBase):
    """ Base plugin for GitHub """

    def __init__(self, config):
        extra_conf_opts = [('alm_api_token', 'GitHub API Token', '')]
        super(GitHubAPI, self).__init__('alm', 'GitHub', config, extra_conf_opts=extra_conf_opts)

    def post_conf_init(self):           
        if self._get_conf('api_token'):
            self.auth_mode = 'api_token'
            self.api_token_header_name = 'Authorization'
            self.config['alm_pass'] = 'token %s' % self._get_conf('api_token')

        super(GitHubAPI, self).post_conf_init()


class GitHubTask(AlmTask):
    """ Representation of a task in GitHub"""

    def __init__(self, task_id, alm_id, status, timestamp, done_statuses):
        self.task_id = task_id
        self.alm_id = alm_id
        self.status = status
        self.timestamp = timestamp
        self.done_statuses = done_statuses  # comma-separated list

    def get_task_id(self):
        return self.task_id

    def get_alm_id(self):
        return self.alm_id

    def get_priority(self):
        return self.priority

    def get_status(self):
        """ Translates GitHub status into SDE status """
        if self.status in self.done_statuses:
            return 'DONE'
        else:
            return 'TODO'

    def get_timestamp(self):
        """ Returns a datetime object """
        return datetime.strptime(self.timestamp, '%Y-%m-%dT%H:%M:%SZ')


class GitHubConnector(AlmConnector):
    alm_name = 'GitHub'
    GITHUB_ISSUE_LABEL = 'github_issue_label'
    ALM_NEW_STATUS = 'github_new_status'
    ALM_DONE_STATUSES = 'github_done_statuses'
    GITHUB_DUPLICATE_LABEL = 'github_duplicate_label'
    ALM_PROJECT_VERSION = 'alm_project_version'
    GITHUB_REPO_OWNER = 'github_repo_owner'
    ALM_PRIORITY_MAP = 'alm_priority_map'
    GITHUB_GROUP_LABEL = 'alm_group_label'

    def __init__(self, config, alm_plugin):
        """ Initializes connection to GitHub """
        super(GitHubConnector, self).__init__(config, alm_plugin)

        config.add_custom_option(self.GITHUB_ISSUE_LABEL, 'Issue type represented'
                                 'by labels on GitHub', default='')
        config.add_custom_option(self.ALM_NEW_STATUS, 'Status to set for new'
                                 'tasks in GitHub', default='open')
        config.add_custom_option(self.ALM_DONE_STATUSES, 'Statuses that '
                                 'signify a task is Done in GitHub',
                                 default='closed')
        config.add_custom_option(self.GITHUB_DUPLICATE_LABEL, 'GitHub label'
                                 'for duplicate issues', default='duplicate')
        config.add_custom_option(self.ALM_PROJECT_VERSION, 'GitHub milestone',
                                 default='')
        config.add_custom_option(self.GITHUB_REPO_OWNER, 'GitHub repository owner',
                                 default='')
        config.add_custom_option(self.ALM_PRIORITY_MAP, 'Customized map from priority in SDE to GITHUB '
                                 '(JSON encoded dictionary of strings)', default='')
        config.add_custom_option(self.GITHUB_GROUP_LABEL, 'GitHub label for issues generated by SDElements',
                                 default='SD Elements')

    def initialize(self):
        super(GitHubConnector, self).initialize()

        # Verify that the configuration options are set properly
        for item in [self.ALM_NEW_STATUS, self.ALM_DONE_STATUSES, self.GITHUB_DUPLICATE_LABEL,
                     self.GITHUB_REPO_OWNER]:
            if not self.config[item]:
                raise AlmException('Missing %s in configuration' % item)

        self.config[self.ALM_DONE_STATUSES] = self.config[self.ALM_DONE_STATUSES].split(',')
        self.config.process_json_str_dict(self.ALM_PRIORITY_MAP)

        if not self.config[self.ALM_PRIORITY_MAP]:
            self.config[self.ALM_PRIORITY_MAP] = GITHUB_DEFAULT_PRIORITY_MAP

        for key in self.config[self.ALM_PRIORITY_MAP]:
            if not RE_MAP_RANGE_KEY.match(key):
                raise AlmException('Unable to process %s (not a JSON dictionary). Reason: Invalid range key %s'
                                   % (self.ALM_PRIORITY_MAP, key))

    def alm_connect_server(self):
        """ Verifies that GitHub connection works """
        # Check if user can successfully authenticate and retrieve user profile
        try:
            user_info = self.alm_plugin.call_api('user')
        except APIError, err:
            raise AlmException('Unable to connect to GitHub service (Check'
                               'server URL, user, pass). Reason: %s' %
                               str(err))

        if user_info.get('message'):
            raise AlmException('Could not authenticate GitHub user %s: %s' %
                              (self.config['alm_user'], user_info['message']))

    def alm_connect_project(self):
        """ Verifies that the GitHub repo exists """
        self.project_uri = '%s/%s' % (urlencode_str(self.config[self.GITHUB_REPO_OWNER]),
                                      urlencode_str(self.config['alm_project']))

        # Check if GitHub repo is accessible
        try:
            repo_info = self.alm_plugin.call_api('repos/%s' % self.project_uri)
        except APIError, err:
            raise AlmException('Unable to find GitHub repo. Reason: %s' % err)

        if repo_info.get('message'):
            raise AlmException('Error accessing GitHub repository %s: %s' %
                               self.project_uri, repo_info['message'])

    def github_get_milestone_id(self, milestone_name):
        if not milestone_name:
            return None

        try:
            milestone_list = self.alm_plugin.call_api('repos/%s/milestones' %
                                                      self.project_uri)
        except APIError, err:
            logger.error(err)
            raise AlmException('Unable to get milestone %s from GitHub' %
                               milestone_name)

        for milestone in milestone_list:
            if milestone['title'] == milestone_name:
                return milestone['number']

        raise AlmException('Unable to find milestone %s from GitHub' %
                           milestone_name)

    def alm_get_task(self, task):
        task_id = task['title']

        try:
            # We need to perform 2 API calls to search open and closed issues
            open_issues = self.alm_plugin.call_api('legacy/issues/search/%s/%s/%s' %
                                                   (self.project_uri,
                                                    self.config[self.ALM_NEW_STATUS],
                                                    urlencode_str(task_id)))
            closed_issues = self.alm_plugin.call_api('legacy/issues/search/%s/%s/%s' %
                                                     (self.project_uri,
                                                      self.config[self.ALM_DONE_STATUSES][0],
                                                      urlencode_str(task_id)))
        except APIError, err:
            logger.error(err)
            raise AlmException('Unable to get task %s from GitHub' % task_id)

        issues_list = open_issues['issues']
        issues_list.extend(closed_issues['issues'])

        if (not issues_list):
            return None

        index = 0

        # Prune list of issues labeled as duplicate
        while index < len(issues_list):
            issue = issues_list[index]
            duplicate_label = self.config[self.GITHUB_DUPLICATE_LABEL]

            if issue['labels'].count(duplicate_label) > 0:
                issues_list.pop(index)
            else:
                index = index + 1

        if len(issues_list) > 1:
            logger.warning('Found multiple issues with the title %s that are not labeled as duplicates.'
                           'Selecting the first task found with id %s' % (task_id, issue['number']))
        elif not issues_list:
            return None

        logger.info('Found task: %s', task_id)
        return GitHubTask(task_id,
                          issues_list[0]['number'],
                          issues_list[0]['state'],
                          issues_list[0]['updated_at'],
                          self.config[self.ALM_DONE_STATUSES])

    def translate_priority(self, priority):
        """ Translates an SDE priority into a GitHub label """
        pmap = self.config[self.ALM_PRIORITY_MAP]

        if not pmap:
            return None

        try:
            priority = int(priority)
        except (TypeError):
            logger.error('Could not coerce %s into an integer' % priority)
            raise AlmException("Error in translating SDE priority to GitHub label: "
                               "%s is not an integer priority" % priority)

        for key in pmap:
            if '-' in key:
                lrange, hrange = key.split('-')
                lrange = int(lrange)
                hrange = int(hrange)
                if lrange <= priority <= hrange:
                    return pmap[key]
            else:
                if int(key) == priority:
                    return pmap[key]

    def alm_add_task(self, task):
        milestone_name = self.config[self.ALM_PROJECT_VERSION]
        github_priority_label = self.translate_priority(task['priority'])
        github_group_label = self.config[self.GITHUB_GROUP_LABEL]
        github_issue_label = self.config[self.GITHUB_ISSUE_LABEL]
        labels = []
        create_args = {
            'title': task['title'],
            'body': self.sde_get_task_content(task),
        }

        if github_priority_label:
            labels.append(github_priority_label)
        if github_group_label:
            labels.append(github_group_label)
        if github_issue_label:
            labels.append(github_issue_label)
        if labels:
            create_args['labels'] = labels
        if milestone_name:
            create_args['milestone'] = self.github_get_milestone_id(milestone_name)

        try:
            new_issue = self.alm_plugin.call_api('repos/%s/issues' %
                                                 self.project_uri,
                                                 method=self.alm_plugin.URLRequest.POST,
                                                 args=create_args)
            logger.debug('Task %s added to GitHub Project', task['id'])
        except APIError, err:
            raise AlmException('Unable to add task %s to GitHub because of %s'
                               % (task['id'], err))

        if new_issue.get('errors'):
            raise AlmException('Unable to add task GitHub to %s. Reason: %s - %s'
                               % (task['id'], str(new_issue['errors']['code']),
                                  str(new_issue['errors']['field'])))

        # API returns JSON of the new issue
        alm_task = GitHubTask(task['title'],
                              new_issue['number'],
                              new_issue['state'],
                              new_issue['updated_at'],
                              self.config[self.ALM_DONE_STATUSES])

        if (self.config['alm_standard_workflow'] and
                (task['status'] == 'DONE' or task['status'] == 'NA')):
            self.alm_update_task_status(alm_task, task['status'])

        return 'Repository: %s, Issue: %s' % (self.config['alm_project'],
                                              alm_task.get_alm_id())

    def alm_update_task_status(self, task, status):
        if not task or not self.config['alm_standard_workflow']:
            logger.debug('Status synchronization disabled')
            return

        if status == 'DONE' or status == 'NA':
            alm_state = self.config[self.ALM_DONE_STATUSES][0]
        elif status == 'TODO':
            alm_state = self.config[self.ALM_NEW_STATUS]

        update_args = {
            'state': alm_state
        }

        try:
            result = self.alm_plugin.call_api('repos/%s/issues/%s' % (self.project_uri, task.get_alm_id()),
                                              args=update_args, method=URLRequest.POST)
        except APIError, err:
            raise AlmException('Unable to update task status to %s '
                               'for issue: %s in GitHub because of %s' %
                               (status, task.get_alm_id(), err))

        if (result and result.get('errors')):
            raise AlmException('Unable to update status of task %s to %s.'
                               'Reason: %s - %s' %
                               (task['id'], status,
                                str(result['errors']['code']),
                                str(result['errors']['field'])))

        logger.debug('Status changed to %s for task %s in GitHub' %
                     (status, task.get_alm_id()))

    def alm_disconnect(self):
        pass
