#!/usr/bin/python
#
# Version 0.01
# Rohit Sethi
# Copyright SDElements Inc
#
# Proof of concept for extensible two way
# integration with JIRA

import sys, os
sys.path.append(os.path.split(os.path.split(os.path.abspath(__file__))[0])[0])

from sdelib.conf_mgr import config
from sdelib.interactive_plugin import PlugInExperience
from sdelib.apiclient import APIBase, URLRequest
from alm_plugin_base import AlmException, AlmTask, AlmConnector 
from sdelib.conf_mgr import Config
import logging


class JIRABase(APIBase):
    """ Base plugin for JIRA """

    def __init__(self, config):
        APIBase.__init__(self, config)
        self.base_uri = '%s://%s/rest/api/2' % ((self.config['method'],
                                                    self.config['server']))
        
class JIRAConfig(Config):

    def set_settings(self, config):
        self.settings = config.copy()
        
class JIRATask(AlmTask):
     """
     Representation of a task in JIRA
     """
     def __init__(self, task_id, alm_id, priority, status, timestamp):
          self.task_id = task_id
          self.alm_id = alm_id
          self.priority = priority
          self.status = status
          self.timestampe = timestamp
     
     def get_task_id(self):
          return self.task_id

     def get_alm_id(self):
          return self.alm_id
     
     def get_priority(self):
         return self.priority        
          
     def get_status(self):
         #Translates JIRA priority into SDE priority
         if (self.status == 'Open' or
             self.status == 'In Progress' or
             self.status == 'Incomplete' or
             self.status == 'Reopened'):
             return 'TODO'
         elif (self.status == 'Fixed'):
             return 'DONE'
         else:
             return 'NA'      

     def get_timestamp(self):
          return self.timestamp
    
     @classmethod
     def translate_priority(cls, priority):
        """ Translates an SDE priority into a JIRA priority """
        priority_int = 0
        try:
            priority_int = int(priority)
        except (TypeError):
            logging.error('' % priority)
            raise AlmException("Error in translating SDE priority to JIRA: " +
                               "%s is not an integer priority" % priority)
        
        if (priority_int == 10):
            return 'Blocker'
        elif (7 <= priority_int <=9):
            return 'Critical'
        elif (5 <= priority_int <=6):
            return 'Major'
        elif (3 <= priority_int <=4):
            return 'Minor'
        else:
            return 'Trivial'




class JIRAConnector(AlmConnector):
    """
     Connects to a JIRA instance
    """
    def alm_name(self):
          return "JIRA"

    def alm_connect(self):
        #No need to setup connection
        pass

    def alm_get_task (self, task):
        task_id = task['title'].partition(':')[0]
        ret_err, ret_val = self.alm_plugin._call_api(
            'search?jql=project%%3D\'%s\'%%20AND%%20summary~\'%s\''
                                           % (self.configuration['project'],
                                              task_id))
         
        if (ret_err):
            logging.info("Error return: %s, %s" % (result[0], result[1]))
            raise AlmException("Unable to get task %s from JIRA")

        num_results = ret_val['total']
        if (num_results == 0):
            #No result was found from query
            return None
        else:
            #We will use the first result from the query
            jtask = ret_val['issues'][0]
            
            logging.debug("Found task with: %s %s %s %s %s" % (task['id'],
                            jtask['key'],
                            jtask['fields']['priority']['name'],
                            jtask['fields']['status']['name'],
                            jtask['fields']['updated']))
            return JIRATask(task['id'],
                            jtask['key'],
                            jtask['fields']['priority']['name'],
                            jtask['fields']['status']['name'],
                            jtask['fields']['updated'])
            
        
       
          
    def alm_add_task(self, task):     
         self.alm_plugin._call_api('issue',method=URLRequest.POST,
                               args={'fields':{'project':
                                      {'key':self.configuration['project']},
                                     'summary':task['title'],
                                     'description':task['content'],
                                     'priority':{'name':JIRATask.
                                                 translate_priority(
                                                     task['priority'])},  
                                     'issuetype':{'id':'1'}}})[1]

    def alm_update_task_status(self, task, status):

          alm_task_row = self.find_matching_row(task)
 
          if (alm_task_row):
               writer = csv.DictWriter(self.csv_file, self.fields)
               writer[alm_task_row]['status'] = status
          

    def alm_disconnect(self):
          pass



def main(argv):
    ret = config.parse_args(argv)
    if not ret:
        sys.exit(1)
    jira_config = JIRAConfig()
    jira_config.set_settings({'method':'https', 'server':'sdetest.atlassian.net',
              'username':'sdetest', 'password':'YZC9H6etExRj2KNLeUjTNZU3jR',
              'project':'SIM',
              'targets': None,
              'debug_level': 1,
              'skip_hidden': True,
              'interactive': True,
              'askpasswd': False,
              'auth_mode': 'basic',
              'application': None})
    
    jbase = JIRABase(jira_config)
    sde_plugin = PlugInExperience(config)
    jira = JIRAConnector(sde_plugin, jbase, jira_config)
    jira.synchronize()
              
    
if __name__ == "__main__":
    main(sys.argv)
