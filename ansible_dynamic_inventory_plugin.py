import gzip
import json
import ssl
import urllib.request

from pathlib import Path
from re import search
from unittest.mock import MagicMock, patch

from ansible.plugins.inventory import (
    BaseInventoryPlugin,
)  # TODO: Constructable, Cacheable
from ansible.utils.display import Display

## Allow import of pytest to fail
try:
    import pytest
except ImportError:
    pass

## https://docs.ansible.com/ansible/latest/dev_guide/developing_plugins.html
## https://docs.ansible.com/ansible/latest/dev_guide/developing_inventory.html
## https://docs.ansible.com/ansible/latest/inventory_guide/intro_dynamic_inventory.html

display = Display()


class InventoryModule(BaseInventoryPlugin):

    NAME = "kyoobit.dynamic-inventory.plugin"

    def _get_remote_data(self, url: str, **kwargs) -> dict:
        """GET inventory data from a remote API and return parsed JSON data

        url:str
            Remote API endpoint URL

        ca_bundle:str
            Path to a CA bundle file to use for TLS connections
            default: /etc/ssl/certs/ca-bundle.crt

            WARNING: If the default or supplied `ca_bundle` file
            does not exist, TLS certificate validation is disabled!

        insecure:bool
            Disable TLS certificate validation
            default: False
        """

        ## Handle ca root bundles
        insecure = bool(kwargs.get("insecure", False))
        ca_bundle = kwargs.get("ca_bundle", "/etc/ssl/certs/ca-bundle.crt")
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ca_bundle = Path(ca_bundle).expanduser().resolve()
        if insecure and not ca_bundle.exists():
            display.warning(
                f"TLS validation disabled! CA bundle does not exists: {ca_bundle}"
            )
        if not insecure and ca_bundle.exists():
            context.load_verify_locations(ca_bundle)
        else:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

        ## Request the data from the remote API
        ## Create a request which accepts gzip encoding
        ## Include a User-Agent while we're at it
        headers = {
            "Accept-Encoding": "gzip",
            #'Authorization': 'Bearer some-token',
            "User-Agent": "Mozilla 5.0 (compatible)",
        }

        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, context=context) as response:
            ## Handle decompressing gzip content
            if response.getheader("Content-Encoding") == "gzip":
                data = gzip.decompress(response.read())
            else:
                data = response.read()

        if isinstance(data, bytes):
            ## Decode the string into JSON data
            data = data.decode("utf-8")
        if isinstance(data, str):
            ## Decode the bytes into a string
            data = json.loads(data)

        ## Return data in JSON format
        return data

    def parse(self, inventory, loader, path: str, cache=True):
        """Parse the inventory file and populate the inventory with hosts and groups.

        inventory:
            The inventory object with exiting data

        loader:
            Ansible's DataLoader object (can read JSON)

        path:str
            A string with inventory source path which should contain
            'http:/' or 'https:/'

        cache:bool
            boolean indicating whether to read from cache or not
        """
        ## Call the parent class's parse method
        super(InventoryModule, self).parse(inventory, loader, path, cache)

        ## Normalize the path as a lowercase string
        path = str(path).lower()

        ## Parse out a secure URL using 'https:/'
        if path.find("https:/") != -1:
            url = f"https://{path.split('https:/')[-1]}"
        ## Parse out a non-secure URL using 'http:/'
        elif path.find("http:/") != -1:
            url = f"http://{path.split('http:/')[-1]}"
            display.warning(f"Using a non-secure URL: {url}")
        ## `verify_file` shouldn't allow us to get here
        else:
            raise ValueError(
                f"The `path` value does not contain a URL (http/https): {path}"
            )

        ## GET the remote inventory source data from the remote API
        data = self._get_remote_data(url)

        ## Parse out the inventory source data
        ## https://docs.ansible.com/ansible/latest/dev_guide/developing_inventory.html#inventory-object

        ## Handle adding groups and applying group vars
        groups = data.get("groups", {})
        group_vars = data.get("group_vars", {})
        for group in groups.keys():
            ## Add the group to inventory
            self.inventory.add_group(group)
            ## Add group_vars for all to the group
            if group_vars.get("all", False):
                for key, value in group_vars.get("all").items():
                    self.inventory.set_variable(group, key, value)
            ## Add group_vars specific to the group
            if group_vars.get(group, False):
                for key, value in group_vars.get(group).items():
                    self.inventory.set_variable(group, key, value)

        ## Handle adding hosts and applying host vars
        hosts = data.get("hosts", [])
        host_vars = data.get("host_vars", {})
        for host in hosts:
            ## Add the host to inventory
            self.inventory.add_host(host)
            ## Add host_vars for all to the group
            if host_vars.get("all", False):
                for key, value in host_vars.get("all").items():
                    self.inventory.set_variable(host, key, value)
            ## Add host_vars specific to the host
            if host_vars.get(host, False):
                for key, value in host_vars.get(host).items():
                    self.inventory.set_variable(host, key, value)

        ## Handle adding hosts to groups
        for group, members in groups.items():
            for member in members:
                self.inventory.add_child(group, member)

    def verify_file(self, path: str) -> bool:
        """Return true if this is a valid path for parse to consume.

        path:str
            A path string with the inventory source URL

        The path passed is a normalized value passed by the command-line arguments
        using `-i INVENTORY, --inventory INVENTORY, --inventory-file INVENTORY`.

        INVENTORY becomes an absolute file path which is problematic since the path
        is to be used as the URL to the remote API. Here, we just check if the path
        contains 'http:/' or 'https:/' to determine if it's something we should
        parse or not. The path is normalized and the double slash (://) is a single
        slash before we receive the `path` value.
        """
        valid = False
        ## Base class verify provides some sanity checks
        if not super(InventoryModule, self).verify_file(path):
            ## Require a URL pattern to be processed by this plugin
            if search(r"http(s)?:/", str(path).lower()) is not None:
                valid = True
        return valid


## https://docs.python.org/3/library/unittest.mock.html#unittest.mock.Mock
## https://docs.python.org/3/library/unittest.mock.html#magicmock-and-magic-method-support


def test_inventory_module_get_remote_data():
    with patch("urllib.request.urlopen", return_value=MagicMock()) as mock:
        inventory_module = InventoryModule()
        ## Mock the response data
        ## The first return_value is for the context manager __enter__() method
        ## The second return_value is for the urlopen() method
        ## The third return_value is for the read method of the mock response object
        mock.return_value.__enter__.return_value.read.return_value = Path(
            "sample-inventory.json"
        ).read_text()
        data = inventory_module._get_remote_data("https://example.com/inventory.json")
        assert isinstance(data, dict) is True


def test_inventory_module_get_remote_data_bad_url():
    inventory_module = InventoryModule()
    with pytest.raises(ValueError):
        inventory_module._get_remote_data("example.com/inventory.json")


def test_inventory_module_parse():
    inventory_module = InventoryModule()

    ## Mock the _get_remote_data method to return sample data
    sample_inventory_data = json.loads(Path("sample-inventory.json").read_text())
    inventory_module._get_remote_data = MagicMock(return_value=sample_inventory_data)

    ## Mock the inventory and loader objects
    inventory = MagicMock()
    loader = MagicMock()

    ## Call the parse method
    inventory_module.parse(inventory, loader, "https://example.com/inventory.json")

    ## Assert that the expected methods were called
    assert inventory.add_child.called
    assert inventory.add_group.called
    assert inventory.add_host.called
    assert inventory.set_variable.called


def test_inventory_module_parse_bad_path():
    inventory_module = InventoryModule()

    ## Mock the inventory and loader objects
    inventory = MagicMock()
    loader = MagicMock()

    ## Call the parse method
    with pytest.raises(ValueError):
        inventory_module.parse(inventory, loader, "example.com/inventory.json")


def test_inventory_module_verify_file():
    inventory_module = InventoryModule()

    ## Good paths
    assert inventory_module.verify_file("https://example.com/inventory.json") is True
    assert inventory_module.verify_file("http://example.com/inventory.json") is True

    ## Bad paths
    assert inventory_module.verify_file("example.com/inventory.json") is False
    assert inventory_module.verify_file("inventory.json") is False
    assert inventory_module.verify_file("") is False
    assert inventory_module.verify_file(None) is False
