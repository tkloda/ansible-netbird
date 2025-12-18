# Ansible Collection for NetBird

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

An Ansible collection for managing [NetBird](https://netbird.io) self-hosted infrastructure via the [NetBird REST API](https://docs.netbird.io/api).

## Features

This collection provides comprehensive management of NetBird resources:

- **Users** - Create, update, delete regular and service users
- **Groups** - Organize peers into logical groups
- **Peers** - Manage peer settings (SSH, expiration, etc.)
- **Setup Keys** - Create enrollment keys for new peers
- **Policies** - Define network access rules between groups
- **Networks** - Configure network routing with routers and resources
  - IP/CIDR routing (`10.0.0.0/8`, `192.168.1.0/24`)
  - Domain-based routing (`example.com`, `*.corp.example.com`)
  - High availability with multiple routers and metrics
- **Routes** - Manage legacy routes (deprecated, use Networks instead)
- **DNS** - Configure nameserver groups and DNS settings
- **Posture Checks** - Define security compliance requirements
- **Accounts** - Manage account-wide settings
- **Tokens** - Create and manage personal access tokens
- **Info** - Gather information about any resource

## Requirements

- Ansible >= 2.12
- Python >= 3.6
- A NetBird self-hosted instance with API access
- A NetBird Personal Access Token

## Installation

### From Ansible Galaxy (when published)

```bash
ansible-galaxy collection install community.ansible_netbird
```

### From Source

```bash
# Clone the repository
git clone https://github.com/community/ansible-netbird.git

# Build the collection
cd ansible-netbird
ansible-galaxy collection build

# Install the collection
ansible-galaxy collection install community-netbird-1.0.0.tar.gz
```

## Authentication

All modules require API authentication. You can provide credentials in three ways:

### 1. Module Parameters

```yaml
- name: List peers
  community.ansible_netbird.netbird_info:
    api_url: "https://netbird.example.com"
    api_token: "{{ netbird_token }}"
    resource: peers
```

### 2. Environment Variables

```bash
export NETBIRD_API_URL="https://netbird.example.com"
export NETBIRD_API_TOKEN="your-personal-access-token"
```

```yaml
- name: List peers (uses environment variables)
  community.ansible_netbird.netbird_info:
    resource: peers
```

### 3. Role Variables

```yaml
- hosts: localhost
  vars:
    netbird_api_url: "https://netbird.example.com"
    netbird_api_token: "{{ vault_netbird_token }}"
  roles:
    - community.ansible_netbird
```

## Modules

### netbird_user

Manage NetBird users (regular and service users).

```yaml
# Create a regular user
- name: Create user
  community.ansible_netbird.netbird_user:
    api_url: "{{ netbird_api_url }}"
    api_token: "{{ netbird_api_token }}"
    email: "user@example.com"
    name: "John Doe"
    role: "user"
    auto_groups:
      - "developers"
    state: present

# Create a service user
- name: Create service user
  community.ansible_netbird.netbird_user:
    api_url: "{{ netbird_api_url }}"
    api_token: "{{ netbird_api_token }}"
    name: "automation-service"
    role: "admin"
    is_service_user: true
    state: present
```

### netbird_group

Manage NetBird groups.

```yaml
- name: Create a group
  community.ansible_netbird.netbird_group:
    api_url: "{{ netbird_api_url }}"
    api_token: "{{ netbird_api_token }}"
    name: "production-servers"
    peers:
      - "peer-id-1"
      - "peer-id-2"
    state: present
```

### netbird_peer

Manage NetBird peer settings.

```yaml
- name: Configure peer
  community.ansible_netbird.netbird_peer:
    api_url: "{{ netbird_api_url }}"
    api_token: "{{ netbird_api_token }}"
    peer_id: "peer-id-123"
    name: "production-server-01"
    ssh_enabled: true
    login_expiration_enabled: true
    state: present
```

### netbird_setup_key

Manage NetBird setup keys for peer enrollment.

```yaml
- name: Create reusable setup key
  community.ansible_netbird.netbird_setup_key:
    api_url: "{{ netbird_api_url }}"
    api_token: "{{ netbird_api_token }}"
    name: "server-enrollment"
    key_type: "reusable"
    expires_in: 604800  # 7 days
    auto_groups:
      - "servers"
    ephemeral: false
    state: present
  register: setup_key

- name: Display the key
  debug:
    msg: "Setup key: {{ setup_key.setup_key.key }}"
  when: setup_key.changed
```

### netbird_policy

Manage NetBird access policies.

```yaml
- name: Create access policy
  community.ansible_netbird.netbird_policy:
    api_url: "{{ netbird_api_url }}"
    api_token: "{{ netbird_api_token }}"
    name: "developers-to-servers"
    description: "Allow developers SSH access to servers"
    enabled: true
    rules:
      - name: "ssh-access"
        sources:
          - "developers-group-id"
        destinations:
          - "servers-group-id"
        bidirectional: false
        protocol: "tcp"
        ports:
          - "22"
        action: "accept"
    state: present
```

### netbird_network

Manage NetBird networks with routers and resources. This module provides full routing capabilities, replacing the deprecated routes API.

**Features:**
- Create networks with routing peers (routers)
- Define network resources (IP ranges, CIDRs, or domains)
- Support for domain-based routing including wildcards (`*.example.com`)
- High availability with multiple routers and different metrics

```yaml
# Simple network (container only)
- name: Create simple network
  community.ansible_netbird.netbird_network:
    api_url: "{{ netbird_api_url }}"
    api_token: "{{ netbird_api_token }}"
    name: "office-network"
    description: "Main office network"
    state: present

# Full network with routers and resources
- name: Create network with routing
  community.ansible_netbird.netbird_network:
    api_url: "{{ netbird_api_url }}"
    api_token: "{{ netbird_api_token }}"
    name: "internal-network"
    description: "Corporate internal network"
    routers:
      - peer: "gateway-peer-id"
        metric: 100
        masquerade: true
    resources:
      - address: "10.0.0.0/8"
        name: "internal-range"
        description: "All internal IPs"
        groups:
          - "all-users-group-id"
    state: present

# HA network with multiple routers
- name: Create HA network with failover
  community.ansible_netbird.netbird_network:
    api_url: "{{ netbird_api_url }}"
    api_token: "{{ netbird_api_token }}"
    name: "ha-network"
    description: "High availability network"
    routers:
      - peer_groups:
          - "primary-gateways"
        metric: 100
        masquerade: true
      - peer_groups:
          - "backup-gateways"
        metric: 200
        masquerade: true
    resources:
      - address: "192.168.0.0/16"
        name: "private-networks"
        groups:
          - "developers-group-id"
    state: present

# Domain-based routing
- name: Create network with domain routing
  community.ansible_netbird.netbird_network:
    api_url: "{{ netbird_api_url }}"
    api_token: "{{ netbird_api_token }}"
    name: "internal-services"
    description: "Route traffic to internal domains"
    routers:
      - peer: "dns-gateway-peer-id"
        metric: 100
        masquerade: true
    resources:
      - address: "internal.example.com"
        name: "internal-portal"
        groups:
          - "all-users-group-id"
      - address: "*.corp.example.com"
        name: "corp-subdomains"
        description: "All corporate subdomains"
        groups:
          - "employees-group-id"
    state: present
```

**Router options:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `peer` | str | - | Peer ID (mutually exclusive with `peer_groups`) |
| `peer_groups` | list | - | List of peer group IDs for HA |
| `metric` | int | 9999 | Route priority (lower = higher priority) |
| `masquerade` | bool | false | Enable NAT for traffic through this router |

**Resource options:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `address` | str | required | IP, CIDR, domain, or wildcard (`*.example.com`) |
| `name` | str | '' | Resource name |
| `description` | str | '' | Resource description |
| `enabled` | bool | true | Whether the resource is enabled |
| `groups` | list | [] | Group IDs that can access this resource |

### netbird_route

Manage NetBird routes (deprecated API, prefer `netbird_network` with routers/resources).

```yaml
- name: Create route (legacy)
  community.ansible_netbird.netbird_route:
    api_url: "{{ netbird_api_url }}"
    api_token: "{{ netbird_api_token }}"
    network_id: "internal-route"
    network: "10.0.0.0/8"
    description: "Route to internal network"
    peer_id: "gateway-peer-id"
    metric: 100
    masquerade: true
    enabled: true
    groups:
      - "all-group-id"
    state: present
```

### netbird_dns

Manage NetBird DNS settings and nameserver groups.

```yaml
# Create nameserver group
- name: Create DNS nameserver group
  community.ansible_netbird.netbird_dns:
    api_url: "{{ netbird_api_url }}"
    api_token: "{{ netbird_api_token }}"
    resource_type: nameserver_group
    name: "internal-dns"
    nameservers:
      - ip: "10.0.0.53"
        ns_type: "udp"
        port: 53
    groups: []
    domains:
      - "internal.example.com"
    enabled: true
    state: present

# Update DNS settings
- name: Configure DNS settings
  community.ansible_netbird.netbird_dns:
    api_url: "{{ netbird_api_url }}"
    api_token: "{{ netbird_api_token }}"
    resource_type: settings
    disabled_management_groups:
      - "special-group-id"
    state: present
```

### netbird_posture_check

Manage NetBird posture checks for security compliance.

```yaml
- name: Create version check
  community.ansible_netbird.netbird_posture_check:
    api_url: "{{ netbird_api_url }}"
    api_token: "{{ netbird_api_token }}"
    name: "minimum-version"
    description: "Require minimum NetBird version"
    checks:
      nb_version_check:
        min_version: "0.25.0"
    state: present

- name: Create geo-location check
  community.ansible_netbird.netbird_posture_check:
    api_url: "{{ netbird_api_url }}"
    api_token: "{{ netbird_api_token }}"
    name: "allowed-countries"
    checks:
      geo_location_check:
        locations:
          - country_code: "US"
          - country_code: "DE"
        action: "allow"
    state: present
```

### netbird_account

Manage NetBird account settings.

```yaml
- name: Configure account settings
  community.ansible_netbird.netbird_account:
    api_url: "{{ netbird_api_url }}"
    api_token: "{{ netbird_api_token }}"
    peer_login_expiration_enabled: true
    peer_login_expiration: 604800
    peer_inactivity_expiration_enabled: true
    peer_inactivity_expiration: 2592000
    jwt_groups_enabled: true
    jwt_groups_claim_name: "groups"
    dns_domain: "netbird.example.com"
    state: present
```

### netbird_token

Manage NetBird personal access tokens.

```yaml
- name: Create access token
  community.ansible_netbird.netbird_token:
    api_url: "{{ netbird_api_url }}"
    api_token: "{{ netbird_api_token }}"
    user_id: "user-id-123"
    name: "automation-token"
    expires_in: 365
    state: present
  register: new_token

- name: Display token
  debug:
    msg: "Token: {{ new_token.token.plain_token }}"
  when: new_token.changed
```

### netbird_info

Gather information about NetBird resources.

```yaml
- name: Get all peers
  community.ansible_netbird.netbird_info:
    api_url: "{{ netbird_api_url }}"
    api_token: "{{ netbird_api_token }}"
    resource: peers
  register: peers

- name: Get all groups
  community.ansible_netbird.netbird_info:
    api_url: "{{ netbird_api_url }}"
    api_token: "{{ netbird_api_token }}"
    resource: groups
  register: groups

- name: Get current user
  community.ansible_netbird.netbird_info:
    api_url: "{{ netbird_api_url }}"
    api_token: "{{ netbird_api_token }}"
    resource: current_user
  register: me
```

Available resources: `accounts`, `users`, `peers`, `groups`, `setup_keys`, `policies`, `networks`, `routes`, `dns_nameservers`, `dns_settings`, `posture_checks`, `events`, `countries`, `current_user`

## Role Usage

The collection includes a role for declarative configuration:

```yaml
- hosts: localhost
  vars:
    netbird_api_url: "https://netbird.example.com"
    netbird_api_token: "{{ vault_netbird_token }}"
    
    netbird_groups:
      - name: "developers"
        state: present
      - name: "production"
        state: present
    
    netbird_setup_keys:
      - name: "server-key"
        key_type: "reusable"
        expires_in: 604800
        state: present
    
    netbird_policies:
      - name: "allow-all"
        enabled: true
        rules:
          - name: "all-traffic"
            sources: ["group-id-1"]
            destinations: ["group-id-2"]
            protocol: "all"
            action: "accept"
        state: present
    
    # Networks with routing (replaces deprecated routes)
    netbird_networks:
      - name: "internal-network"
        description: "Corporate internal network"
        routers:
          - peer: "gateway-peer-id"
            metric: 100
            masquerade: true
        resources:
          - address: "10.0.0.0/8"
            name: "internal-range"
            groups: ["developers-group-id"]
          - address: "*.internal.example.com"
            name: "internal-domains"
            groups: ["developers-group-id"]
        state: present

  roles:
    - community.ansible_netbird
```

See `defaults/main.yml` for all available role variables.

## Examples

The `examples/` directory contains complete playbook examples:

- `basic_setup.yml` - Basic groups, keys, and policies setup
- `full_infrastructure.yml` - Complete infrastructure configuration using the role
- `dynamic_policies.yml` - Create policies based on existing groups
- `inventory_from_netbird.yml` - Export peers as Ansible inventory
- `peer_management.yml` - Manage and audit peers

## API Reference

This collection implements the [NetBird REST API](https://docs.netbird.io/api). Refer to the official documentation for detailed information about:

- [Authentication](https://docs.netbird.io/api/guides/authentication)
- [Accounts](https://docs.netbird.io/api/resources/accounts)
- [Users](https://docs.netbird.io/api/resources/users)
- [Peers](https://docs.netbird.io/api/resources/peers)
- [Groups](https://docs.netbird.io/api/resources/groups)
- [Setup Keys](https://docs.netbird.io/api/resources/setup-keys)
- [Policies](https://docs.netbird.io/api/resources/policies)
- [Networks](https://docs.netbird.io/api/resources/networks)
- [DNS](https://docs.netbird.io/api/resources/dns)
- [Posture Checks](https://docs.netbird.io/api/resources/posture-checks)
- [Events](https://docs.netbird.io/api/resources/events)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This collection is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## Support

- [NetBird Documentation](https://docs.netbird.io)
- [NetBird GitHub](https://github.com/netbirdio/netbird)
- [NetBird Community](https://netbird.io/community)
