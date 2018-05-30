"""CloudMan 2.0 application plugin implementation."""
import json
import jsonmerge
import os
import paramiko
import shutil
import socket
import subprocess
import time
from io import StringIO
from paramiko.ssh_exception import AuthenticationException
from paramiko.ssh_exception import BadHostKeyException
from paramiko.ssh_exception import SSHException
import requests
from retrying import retry
from string import Template

from django.conf import settings
from djcloudbridge.view_helpers import get_credentials_from_dict
from git import Repo

from .simple_web_app import SimpleWebAppPlugin

from celery.utils.log import get_task_logger
log = get_task_logger(__name__)


class CloudMan2AppPlugin(SimpleWebAppPlugin):
    """CloudLaunch appliance implementation for CloudMan 2.0."""

    @staticmethod
    def validate_app_config(provider, name, cloud_config, app_config):
        """Format any app-specific configurations."""
        return super(CloudMan2AppPlugin,
                     CloudMan2AppPlugin).validate_app_config(
                         provider, name, cloud_config, app_config)

    @staticmethod
    def sanitise_app_config(app_config):
        """Sanitize any app-specific data that will be stored in the DB."""
        return super(CloudMan2AppPlugin,
                     CloudMan2AppPlugin).sanitise_app_config(app_config)

    def _remove_known_host(self, host):
        """
        Remove a host from ~/.ssh/known_hosts.

        :type host: ``str``
        :param host: Hostname or IP address of the host to remove from the
                     known hosts file.

        :rtype: ``bool``
        :return: True if the host was successfully removed.
        """
        cmd = "ssh-keygen -R {0}".format(host)
        p = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        (out, err) = p.communicate()
        if p.wait() == 0:
            return True
        return False

    @retry(retry_on_result=lambda result: result is False, wait_fixed=5000,
           stop_max_delay=180000)
    def _check_ssh(self, host, pk=None, user='ubuntu'):
        """
        Check for ssh availability on a host.

        :type host: ``str``
        :param host: Hostname or IP address of the host to check.

        :type pk: ``str``
        :param pk: Private portion of an ssh key.

        :type user: ``str``
        :param user: Username to use when trying to login.

        :rtype: ``bool``
        :return: True if ssh connection was successful.
        """
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        pkey = None
        if pk:
            if 'RSA' not in pk:
                # AWS at least does not specify key type yet paramiko requires
                pk = pk.replace(' PRIVATE', ' RSA PRIVATE')
            key_file_object = StringIO(pk)
            pkey = paramiko.RSAKey.from_private_key(key_file_object)
            key_file_object.close()
        try:
            log.info("Trying to ssh {0}@{1}".format(user, host))
            ssh.connect(host, username=user, pkey=pkey)
            self._remove_known_host(host)
            return True
        except (BadHostKeyException, AuthenticationException,
                SSHException, socket.error) as e:
            log.warn("ssh connection exception for {0}: {1}".format(host, e))
        self._remove_known_host(host)
        return False

    def _run_playbook(self, playbook, inventory, host, pk, user='ubuntu',
                      playbook_vars=None):
        """
        Run an Ansible playbook to configure a host.

        First clone a playbook from the supplied repo if not already
        available, configure the Ansible inventory, and run the playbook.

        The method assumes ``ansible-playbook`` system command is available.

        :type playbook: ``str``
        :param playbook: A URL of a git repository where the playbook resides.

        :type inventory: ``str``
        :param inventory: A URL pointing to a string ``Template``-like file
                          that will be used for running the playbook. The
                          file should have defined variables for ``host`` and
                          ``user``.

        :type playbook_vars: ``list`` of tuples
        :param playbook_vars: A list of key/value tuples with variables to pass
                              to the playbook via command line arguments
                              (i.e., --extra-vars key=value).

        :type host: ``str``
        :param host: Hostname or IP of a machine as the playbook target.

        :type pk: ``str``
        :param pk: Private portion of an ssh key.

        :type user: ``str``
        :param user: Target host system username with which to login.
        """
        # Clone the repo in its own dir if multiple tasks run simultaneously
        # The path must be to a folder that doesn't already contain a git repo,
        # including any parent folders
        repo_path = '/tmp/cloudlaunch_plugin_runners/rancher_ansible_%s' % host
        try:
            log.info("Delete plugin runner folder %s if not empty", repo_path)
            shutil.rmtree(repo_path)
        except FileNotFoundError:
            pass
        # Ensure the playbook is available
        log.info("Cloning Ansible playbook %s to %s", playbook, repo_path)
        Repo.clone_from(playbook, to_path=repo_path)
        # Create a private ssh key file
        pkf = os.path.join(repo_path, 'pk')
        with os.fdopen(os.open(pkf, os.O_WRONLY | os.O_CREAT, 0o600),
                       'w') as f:
            f.writelines(pk)
        # Create an inventory file
        r = requests.get(inventory)
        inv = Template((r.content).decode('utf-8'))
        inventory_path = os.path.join(repo_path, 'inventory')
        with open(inventory_path, 'w') as f:
            log.info("Creating inventory file %s", inventory_path)
            f.writelines(inv.substitute({'host': host, 'user': user}))
        # Run the playbook
        cmd = "cd {0} && ansible-playbook -i inventory playbook.yml".format(
            repo_path)
        for pev in playbook_vars or []:
            cmd += " --extra-vars {0}={1}".format(pev[0], pev[1])
        log.info("Running Ansible with command %s", cmd)
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
        (out, _) = p.communicate()
        p_status = p.wait()
        log.info("Playbook stdout: %s\nstatus: %s", out, p_status)
        if not settings.DEBUG:
            log.info("Deleting ansible playbook %s", repo_path)
            shutil.rmtree(repo_path)
        return (p_status, out)

    def _configure_host(self, name, task, app_config, provider_config):
        log.debug("Running CloudMan2AppPlugin _configure_host for %s", name)
        host = provider_config.get('host_address')
        user = provider_config.get('ssh_user')
        ssh_private_key = provider_config.get('ssh_private_key')
        if settings.DEBUG:
            log.info("Using config ssh key:\n%s", ssh_private_key)
        task.update_state(
            state='PROGRESSING',
            meta={'action': 'Waiting for ssh on host {0}...'.format(host)})
        self._check_ssh(host, pk=ssh_private_key, user=user)
        task.update_state(
            state='PROGRESSING',
            meta={'action': 'Booting CloudMan on host {0}...'.format(host)})
        playbook = app_config.get('config_appliance', {}).get('repository')
        inventory = app_config.get(
            'config_appliance', {}).get('inventoryTemplate')
        cloud_info = get_credentials_from_dict(
            provider_config['cloud_provider'].config.copy())
        # Combine bootstrap data to have the following keys: `config_app`,
        # `credentials`, and `cloud`
        cm_bd = {'config_app': app_config, **cloud_info}
        playbook_vars = [
            ('rancher_server', host),
            ('rancher_pwd', app_config.get('config_cloudman2', {}).get(
                'clusterPassword')),
            ('cm_bootstrap_data', "'{0}'".format(json.dumps(cm_bd)))
        ]
        self._run_playbook(playbook, inventory, host, ssh_private_key, user,
                           playbook_vars)
        result = {}
        result['cloudLaunch'] = {'applicationURL':
                                 'https://{0}:4430/'.format(host)}
        task.update_state(
            state='PROGRESSING',
            meta={'action': "Waiting for Rancher to become available at %s"
                            % result['cloudLaunch']['applicationURL']})
        self.wait_for_http(result['cloudLaunch']['applicationURL'])
        return result
