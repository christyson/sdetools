#!/usr/bin/python
import sys
from base_integrator import BaseIntegrator
from sdelib.conf_mgr import config
from xml.dom import minidom

REQUIRED_ATTRIBS = ['issueid', 'cweid', 'categoryid', 'categoryname', 'description', 'severity', 'module']
LOCATION_ATTRIBS = ['sourcefilepath', 'sourcefile', 'line', 'location']
SOURCE_ID = "VC"

class VeracodeIntegrator(BaseIntegrator):

    def __init__(self, config):
        BaseIntegrator.__init__(self, config)
        self.raw_findings = []

    def parse(self, file_name):
        base = minidom.parse(file_name)
        detailed_reports = base.getElementsByTagName('detailedreport')
        if len(detailed_reports) != 1:
            raise Exception('An unexpected number of detailedreport nodes found (%d)' % (len(detailed_reports)))
        dr = detailed_reports[0]
        self.report_id = "%s: %s (%s-b%s) %s" % (SOURCE_ID,dr.attributes['app_name'].value,dr.attributes['app_id'].value,dr.attributes['build_id'].value,dr.attributes['generation_date'].value)

        for node in base.getElementsByTagName('flaw'):
            entry = {}
            for attr in REQUIRED_ATTRIBS:
                if attr not in node.attributes.keys():
                    raise Exception('Required attribute %s missing' % (attr))
                else:
                    entry[attr] = node.attributes[attr].value
            for attr in LOCATION_ATTRIBS:
                if attr in  node.attributes.keys():
                    entry[attr] = node.attributes[attr].value

            self.raw_findings.append(entry)

    def output_findings(self):
        for item in self.raw_findings:
            print '%5s,%5s,%5s' % (item['issueid'], item['cweid'], item['categoryid'])
            print item['description'][:120]

    def get_findings(self):
        return self.raw_findings

    def map_findings(self):
        for item in self.raw_findings:
            print '%5s,%5s,%5s,%5s' % (self.map_finding(item['cweid']), item['issueid'], item['cweid'], item['categoryid'])
            print item['description'][:120]

def main(argv):
    ret = config.parse_args(argv)
    if not ret:
        sys.exit(1)
    if len(config['targets']) != 2:
        print "Please specify mapping file and veracode XML report file arguments"
        sys.exit(1)
    vcInt = VeracodeIntegrator(config)
    vcInt.load_mapping_from_csv(config['targets'][0])
    vcInt.parse(config['targets'][1])
    vcInt.apply_findings(False)

if __name__ == "__main__":
    main(sys.argv)

