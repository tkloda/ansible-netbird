#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Community
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Ansible module for managing NetBird networks."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: netbird_network
short_description: Manage NetBird networks
description:
  - Create, update, and delete networks in NetBird.
  - Networks are used to define routing configurations.
version_added: "1.0.0"
author:
  - Community
options:
  state:
    description:
      - The desired state of the network.
    type: str
    choices: ['present', 'absent']
    default: present
  network_id:
    description:
      - The unique identifier of the network.
      - Required when state is absent or when updating by ID.
    type: str
  name:
    description:
      - Name of the network.
      - Required when creating a new network.
    type: str
  description:
    description:
      - Description of the network.
    type: str
    default: ''
extends_documentation_fragment:
  - community.netbird.netbird
requirements:
  - python >= 3.6
'''

EXAMPLES = r'''
- name: Create a network
  community.netbird.netbird_network:
    api_url: "https://netbird.example.com"
    api_token: "{{ netbird_token }}"
    name: "office-network"
    description: "Main office network"
    state: present

- name: Update network description
  community.netbird.netbird_network:
    api_url: "https://netbird.example.com"
    api_token: "{{ netbird_token }}"
    network_id: "network-id-123"
    description: "Updated office network description"
    state: present

- name: Delete a network
  community.netbird.netbird_network:
    api_url: "https://netbird.example.com"
    api_token: "{{ netbird_token }}"
    network_id: "network-id-123"
    state: absent
'''

RETURN = r'''
network:
  description: The network object.
  returned: success
  type: dict
  contains:
    id:
      description: Network ID.
      type: str
    name:
      description: Network name.
      type: str
    description:
      description: Network description.
      type: str
    routers:
      description: List of routers in the network.
      type: list
    resources:
      description: List of resources in the network.
      type: list
    routing_peers_count:
      description: Number of routing peers.
      type: int
    resources_count:
      description: Number of resources.
      type: int
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.community.netbird.plugins.module_utils.netbird_api import (
    NetBirdAPI,
    NetBirdAPIError,
    netbird_argument_spec
)


def find_network_by_name(api, name):
    """Find a network by name."""
    networks, _ = api.list_networks()
    for network in networks:
        if network.get('name') == name:
            return network
    return None


def network_needs_update(current, params):
    """Check if network needs to be updated."""
    if params.get('name') is not None and current.get('name') != params['name']:
        return True
    if params.get('description') is not None and current.get('description') != params['description']:
        return True
    return False


def run_module():
    """Main module execution."""
    argument_spec = netbird_argument_spec()
    argument_spec.update(
        state=dict(type='str', choices=['present', 'absent'], default='present'),
        network_id=dict(type='str'),
        name=dict(type='str'),
        description=dict(type='str', default='')
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[
            ('network_id', 'name'),
        ]
    )

    api = NetBirdAPI(
        module,
        module.params['api_url'],
        module.params['api_token'],
        module.params['validate_certs']
    )

    state = module.params['state']
    network_id = module.params['network_id']
    name = module.params['name']
    description = module.params['description']

    result = dict(
        changed=False,
        network={}
    )

    try:
        # Find existing network
        existing_network = None
        if network_id:
            try:
                existing_network, _ = api.get_network(network_id)
            except NetBirdAPIError as e:
                if e.status_code != 404:
                    raise
        elif name:
            existing_network = find_network_by_name(api, name)

        if state == 'absent':
            if existing_network:
                if not module.check_mode:
                    api.delete_network(existing_network['id'])
                result['changed'] = True
                result['msg'] = 'Network deleted successfully'
            module.exit_json(**result)

        # state == 'present'
        if existing_network:
            # Check if update is needed
            update_params = {
                'name': name,
                'description': description
            }
            
            if network_needs_update(existing_network, update_params):
                if not module.check_mode:
                    network, _ = api.update_network(
                        existing_network['id'],
                        name=name,
                        description=description
                    )
                    result['network'] = network
                else:
                    result['network'] = existing_network
                result['changed'] = True
            else:
                result['network'] = existing_network
        else:
            # Create new network
            if not name:
                module.fail_json(msg="name is required when creating a new network")
            
            if not module.check_mode:
                network, _ = api.create_network(
                    name=name,
                    description=description
                )
                result['network'] = network
            result['changed'] = True

        module.exit_json(**result)

    except NetBirdAPIError as e:
        module.fail_json(msg=str(e), status_code=e.status_code, response=e.response)


def main():
    run_module()


if __name__ == '__main__':
    main()

