# Ansible Dynamic Inventory Plugin

The `ansible_dynamic_inventory_plugin.py` Python script is an Ansible inventory plugin which allows the inventory details to be retrieved from a HTTP service able to return JSON data. The `sample-inventory.json` file contains a minimal example of the expected JSON payload this plugin will parse. The only required field node is the `hosts` list of host names. The plugin only triggers on inventory values that start with `http` or `https`.

The plugin needs to be installed and enabled to function in Ansible. Once installed and enabled you can pass the plugin a URL using the `-i/--inventory` argument.

Example usage:
```shell
ansible-inventory -i https://some-cmdb.example.com/inventory --graph --vars
```

## Requirements

* Python 3
* Python ansible module

Everything else in the `ci-requirements.txt` file is used for continuous integration testing.

## Install the dynamic inventory plugin

Copy or symbolically link the `ansible_dynamic_inventory_plugin.py` Python script into the Ansible _configured module search path_ to install the plugin. This could be the user account which is running ansible on a control node or a global path on a control node.

You can locate the _configured module search path_ used by your Ansible installation using: `ansible --version`.

```shell
ansible --version | grep 'configured module search path'
```
Example output:
```shell
(venv) ansible_dynamic_inventory_plugin % ansible --version | grep 'configured module search path'
  configured module search path = ['/home/auser/.ansible/plugins/modules', '/usr/share/ansible/plugins/modules']
```

Example of using a symbolic link to install the plugin in the current users `~/.ansible` directory:

```shell
mkdir -p $HOME/.ansible/plugins/inventory
ln -sf $(pwd)/ansible_dynamic_inventory_plugin.py $HOME/.ansible/plugins/inventory/
```

### Enable the dynamic inventory plugin

Enable the plugin by adding the plugin filename `ansible_dynamic_inventory_plugin` (sans .py) to your `ansible.cfg`. By placing plugin filename first in the `enable_plugins` list the plugin will be used before other options. The plugin only triggers on inventory values that start with `http` or `https`. See Ansible's documentation on [Enabling Inventory Plugins](http://docs.ansible.com/ansible/latest/plugins/inventory.html#enabling-inventory-plugins) for additional options.

`ansible.cfg`
```yaml
[inventory]
## Default: enable_plugins = host_list, script, auto, yaml, ini, toml
enable_plugins = ansible_dynamic_inventory_plugin, host_list, script, auto, yaml, ini, toml
```

#### Running a test API to validate the dynamic inventory plugin

A super-simple FastAPI HTTP service can be run using the `ansible_dynamic_inventory_api.py` Python script.

Install the dependencies:
```shell
python3 -m venv venv
source ./venv/bin/activate
python -m pip install --upgrade pip ansible "fastapi[standard]"
```
Run the simple API service:
```shell
fastapi dev ansible_dynamic_inventory_api.py
```
Run a request from ansible for the inventory:
```shell
ansible-inventory -i http://127.0.0.1:8000/inventory --graph
```

Example output:

```shell
(venv) python_ansible_inventory_plugin % ansible-inventory -i http://127.0.0.1:8000/inventory --graph --vars 
WARNING:root:Using a non-secure URL: http://127.0.0.1:8000/inventory
@all:
  |--@ungrouped:
  |  |--host005
  |--@group001:
  |  |--host001
  |  |  |--{ansible_host = host001.example.com}
  |  |  |--{ansible_private_key_file = {{ lookup('env','HOME') }}/.ssh/host001.example.com_ecdsa}
  |  |  |--{var01 = bar}
  |  |--host002
  |  |  |--{var01 = bar}
  |  |--{var01 = bar}
  |--@group002:
  |  |--host003
  |  |  |--{var01 = foo}
  |  |--host004
  |  |  |--{var01 = foo}
  |  |--{var01 = foo}
```

## Sample Inventory
The `sample-inventory.json` file is an example JSON inventory response the dynamic inventory plugin is able to parse. The only required field node is the `hosts` list of host names.
```json
{
  "group_vars": {
    "all": {
      "var01": "foo"
    },
    "group001": {
      "var01": "bar"
    }
  },
  "groups": {
    "group001": [
      "host001",
      "host002"
    ],
    "group002": [
      "host003",
      "host004"
    ]
  },
  "host_vars": {
    "host001": {
      "ansible_host": "host001.example.com",
      "ansible_private_key_file": "{{ lookup('env','HOME') }}/.ssh/host001.example.com_ecdsa"
    }
  },
  "hosts": [
    "host001",
    "host002",
    "host003",
    "host004",
    "host005"
  ]
}
```