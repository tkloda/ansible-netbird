#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Community
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Ansible module for managing NetBird policies."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: netbird_policy
short_description: Manage NetBird policies
description:
  - Create, update, and delete policies in NetBird.
  - Policies define network access rules between groups.
version_added: "1.0.0"
author:
  - Community
options:
  state:
    description:
      - The desired state of the policy.
    type: str
    choices: ['present', 'absent']
    default: present
  policy_id:
    description:
      - The unique identifier of the policy.
      - Required when state is absent or when updating by ID.
    type: str
  name:
    description:
      - Name of the policy.
      - Required when creating a new policy.
    type: str
  description:
    description:
      - Description of the policy.
    type: str
    default: ''
  enabled:
    description:
      - Whether the policy is enabled.
    type: bool
    default: true
  rules:
    description:
      - List of policy rules.
      - Each rule defines traffic flow between source and destination groups.
    type: list
    elements: dict
    suboptions:
      name:
        description:
          - Name of the rule.
        type: str
      description:
        description:
          - Description of the rule.
        type: str
      enabled:
        description:
          - Whether the rule is enabled.
        type: bool
        default: true
      sources:
        description:
          - List of source group IDs.
        type: list
        elements: str
      destinations:
        description:
          - List of destination group IDs.
        type: list
        elements: str
      bidirectional:
        description:
          - Whether traffic flows both ways.
        type: bool
        default: true
      protocol:
        description:
          - Network protocol (all, tcp, udp, icmp).
        type: str
        default: all
      ports:
        description:
          - List of destination ports (e.g., ["80", "443", "8000-9000"]).
        type: list
        elements: str
      action:
        description:
          - Action to take (accept, drop).
        type: str
        default: accept
extends_documentation_fragment:
  - community.netbird.netbird
requirements:
  - python >= 3.6
'''

EXAMPLES = r'''
- name: Create a policy allowing all traffic between groups
  community.netbird.netbird_policy:
    api_url: "https://netbird.example.com"
    api_token: "{{ netbird_token }}"
    name: "Allow developers to production"
    description: "Developers can access production servers"
    enabled: true
    rules:
      - name: "developers-to-production"
        sources:
          - "developers-group-id"
        destinations:
          - "production-group-id"
        bidirectional: false
        protocol: "all"
        action: "accept"
    state: present

- name: Create a policy with specific ports
  community.netbird.netbird_policy:
    api_url: "https://netbird.example.com"
    api_token: "{{ netbird_token }}"
    name: "Web traffic only"
    rules:
      - name: "http-https"
        sources:
          - "clients-group-id"
        destinations:
          - "webservers-group-id"
        protocol: "tcp"
        ports:
          - "80"
          - "443"
        action: "accept"
    state: present

- name: Disable a policy
  community.netbird.netbird_policy:
    api_url: "https://netbird.example.com"
    api_token: "{{ netbird_token }}"
    policy_id: "policy-id-123"
    enabled: false
    state: present

- name: Delete a policy
  community.netbird.netbird_policy:
    api_url: "https://netbird.example.com"
    api_token: "{{ netbird_token }}"
    policy_id: "policy-id-123"
    state: absent
'''

RETURN = r'''
policy:
  description: The policy object.
  returned: success
  type: dict
  contains:
    id:
      description: Policy ID.
      type: str
    name:
      description: Policy name.
      type: str
    description:
      description: Policy description.
      type: str
    enabled:
      description: Whether policy is enabled.
      type: bool
    rules:
      description: List of policy rules.
      type: list
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.community.netbird.plugins.module_utils.netbird_api import (
    NetBirdAPI,
    NetBirdAPIError,
    netbird_argument_spec
)


def find_policy_by_name(api, name):
    """Find a policy by name."""
    policies, _ = api.list_policies()
    for policy in policies:
        if policy.get('name') == name:
            return policy
    return None


def policy_needs_update(current, params):
    """Check if policy needs to be updated."""
    if params.get('name') is not None and current.get('name') != params['name']:
        return True
    if params.get('description') is not None and current.get('description') != params['description']:
        return True
    if params.get('enabled') is not None and current.get('enabled') != params['enabled']:
        return True
    # For rules, always update if provided to ensure they match exactly
    if params.get('rules') is not None:
        return True
    return False


def run_module():
    """Main module execution."""
    argument_spec = netbird_argument_spec()
    argument_spec.update(
        state=dict(type='str', choices=['present', 'absent'], default='present'),
        policy_id=dict(type='str'),
        name=dict(type='str'),
        description=dict(type='str', default=''),
        enabled=dict(type='bool', default=True),
        rules=dict(type='list', elements='dict')
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[
            ('policy_id', 'name'),
        ]
    )

    api = NetBirdAPI(
        module,
        module.params['api_url'],
        module.params['api_token'],
        module.params['validate_certs']
    )

    state = module.params['state']
    policy_id = module.params['policy_id']
    name = module.params['name']
    description = module.params['description']
    enabled = module.params['enabled']
    rules = module.params['rules']

    result = dict(
        changed=False,
        policy={}
    )

    try:
        # Find existing policy
        existing_policy = None
        if policy_id:
            try:
                existing_policy, _ = api.get_policy(policy_id)
            except NetBirdAPIError as e:
                if e.status_code != 404:
                    raise
        elif name:
            existing_policy = find_policy_by_name(api, name)

        if state == 'absent':
            if existing_policy:
                if not module.check_mode:
                    api.delete_policy(existing_policy['id'])
                result['changed'] = True
                result['msg'] = 'Policy deleted successfully'
            module.exit_json(**result)

        # state == 'present'
        if existing_policy:
            # Check if update is needed
            update_params = {
                'name': name,
                'description': description,
                'enabled': enabled,
                'rules': rules
            }
            
            if policy_needs_update(existing_policy, update_params):
                if not module.check_mode:
                    policy, _ = api.update_policy(
                        existing_policy['id'],
                        name=name,
                        enabled=enabled,
                        description=description,
                        rules=rules
                    )
                    result['policy'] = policy
                else:
                    result['policy'] = existing_policy
                result['changed'] = True
            else:
                result['policy'] = existing_policy
        else:
            # Create new policy
            if not name:
                module.fail_json(msg="name is required when creating a new policy")
            
            if not module.check_mode:
                policy, _ = api.create_policy(
                    name=name,
                    enabled=enabled,
                    description=description,
                    rules=rules or []
                )
                result['policy'] = policy
            result['changed'] = True

        module.exit_json(**result)

    except NetBirdAPIError as e:
        module.fail_json(msg=str(e), status_code=e.status_code, response=e.response)


def main():
    run_module()


if __name__ == '__main__':
    main()

