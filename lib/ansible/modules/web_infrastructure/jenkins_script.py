#!/usr/bin/python

# encoding: utf-8

# (c) 2016, James Hogarth <james.hogarth@gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.


ANSIBLE_METADATA = {'metadata_version': '1.0',
                    'status': ['preview'],
                    'supported_by': 'community'}


DOCUMENTATION = '''
---
author: James Hogarth
module: jenkins_script
short_description: Executes a groovy script in the jenkins instance
version_added: '2.3'
description:
    - The C(jenkins_script) module takes a script plus a dict of values
      to use within the script and returns the result of the script being run.

options:
  script:
    description:
      - The groovy script to be executed.
        This gets passed as a string Template if args is defined.
    required: true
    default: null
  url:
    description:
      - The jenkins server to execute the script against. The default is a local
        jenkins instance that is not being proxied through a webserver.
    required: false
    default: http://localhost:8080
  validate_certs:
    description:
      - If set to C(no), the SSL certificates will not be validated.
        This should only set to C(no) used on personally controlled sites
        using self-signed certificates as it avoids verifying the source site.
    required: false
    default: True
  user:
    description:
      - The username to connect to the jenkins server with.
    required: false
    default: null
  password:
    description:
      - The password to connect to the jenkins server with.
    required: false
    default: null
  args:
    description:
      - A dict of key-value pairs used in formatting the script.
    required: false
    default: null

notes:
    - Since the script can do anything this does not report on changes.
      Knowing the script is being run it's important to set changed_when
      for the ansible output to be clear on any alterations made.

'''

EXAMPLES = '''
- name: Obtaining a list of plugins
  jenkins_script:
    script: 'println(Jenkins.instance.pluginManager.plugins)'
    user: admin
    password: admin

- name: Setting master using a variable to hold a more complicate script
  vars:
    setmaster_mode: |
        import jenkins.model.*
        instance = Jenkins.getInstance()
        instance.setMode(${jenkins_mode})
        instance.save()

- name: use the variable as the script
  jenkins_script:
    script: "{{ setmaster_mode }}"
    args:
      jenkins_mode: Node.Mode.EXCLUSIVE

- name: interacting with an untrusted HTTPS connection
  jenkins_script:
    script: "println(Jenkins.instance.pluginManager.plugins)"
    user: admin
    password: admin
    url: https://localhost
    validate_certs: no
'''

RETURN = '''
output:
    description: Result of script
    returned: success
    type: string
    sample: 'Result: true'
'''

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import fetch_url
try:
    # python2
    from urllib import urlencode
except ImportError:
    # python3
    from urllib.parse import urlencode

def main():

    module = AnsibleModule(
        argument_spec = dict(
            script = dict(required=True, type="str"),
            url   = dict(required=False, type="str", default="http://localhost:8080"),
            validate_certs = dict(required=False, type="bool", default=True),
            user   = dict(required=False, no_log=True, type="str",default=None),
            password   = dict(required=False, no_log=True, type="str",default=None),
            args   = dict(required=False, type="dict", default=None)
        )
    )


    if module.params['user'] is not None:
        if module.params['password'] is None:
            module.fail_json(msg="password required when user provided")
        module.params['url_username'] = module.params['user']
        module.params['url_password'] = module.params['password']
        module.params['force_basic_auth'] = True


    if module.params['args'] is not None:
        from string import Template
        script_contents = Template(module.params['script']).substitute(module.params['args'])
    else:
        script_contents = module.params['script']


    resp, info = fetch_url(module,
                           module.params['url'] + "/scriptText",
                           data=urlencode({'script': script_contents}),
                           method="POST")

    if info["status"] != 200:
        module.fail_json(msg="HTTP error " + str(info["status"]) + " " + info["msg"])

    result = resp.read()

    if 'Exception:' in result and 'at java.lang.Thread' in result:
        module.fail_json(msg="script failed with stacktrace:\n " + result)

    module.exit_json(
        output = result,
    )



if __name__ == '__main__':
    main()
