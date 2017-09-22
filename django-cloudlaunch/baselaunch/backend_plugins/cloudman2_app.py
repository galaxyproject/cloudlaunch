"""CloudMan 2.0 application plugin implementation."""
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
from string import Template

from django.conf import settings
from git import Repo

from .base_vm_app import BaseVMAppPlugin
from baselaunch import domain_model

from celery.utils.log import get_task_logger
log = get_task_logger(__name__)

# Ansible playbook at this URL will be used to configure a bare-bones VM
ANSIBLE_PLAYBOOK_REPO = 'https://github.com/afgane/Rancher-Ansible'

INVENTORY_TEMPLATE = Template("""
[Rancher]
rancher ansible_ssh_host=${master}

[Agents]

[cluster:children]
Rancher
Agents

[cluster:vars]
ansible_ssh_port=22
ansible_user='${user}'
ansible_ssh_private_key_file=pk
ansible_ssh_extra_args='-o StrictHostKeyChecking=no'
""")


class CloudMan2AppPlugin(BaseVMAppPlugin):
    """CloudLaunch appliance implementation for CloudMan 2.0."""

    def __init__(self):
        """Initialize CloudMan2AppPlugin object."""
        self.base_app = False

    @staticmethod
    def process_app_config(provider, name, cloud_version_config, app_config):
        """Format any app-specific configurations."""
        return super(CloudMan2AppPlugin,
                     CloudMan2AppPlugin).process_app_config(
            provider, name, cloud_version_config, app_config)

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

    def _check_ssh(self, host, pk=None, user='ubuntu'):
        """
        Check for ssh availability on a host.

        :type host: ``str``
        :param host: Hostname or IP address of the host to check.

        :type user: ``str``
        :param user: Username to use when trying to login.

        :type pk: ``str``
        :param pk: Private portion of an ssh key.

        :rtype: ``bool``
        :return: True if ssh connection was successful.
        """
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        pkey = None
        if pk:
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

    def _run_playbook(self, host, pk, user='ubuntu'):
        """
        Run an Ansible playbook to configure a host.

        First clone an playbook repo if not already available, configure the
        Ansible inventory and run the playbook.

        The method assumes ``ansible-playbook`` command is available.

        :type host: ``str``
        :param host: Hostname or IP of a machine as the playbook target.

        :type pk: ``str``
        :param pk: Private portion of an ssh key.

        :type user: ``str``
        :param user: Target host system username with which to login.
        """
        # Clone the repo in its own dir if multiple tasks run simultaneously
        repo_path = './baselaunch/backend_plugins/rancher_ansible_%s' % host
        inventory_path = os.path.join(repo_path, 'inventory')
        # Ensure the playbook is available
        log.info("Cloning Ansible playbook {0} to {1}".format(
                 ANSIBLE_PLAYBOOK_REPO, repo_path))
        Repo.clone_from(ANSIBLE_PLAYBOOK_REPO, to_path=repo_path)
        # Create an inventory file
        pkf = os.path.join(repo_path, 'pk')
        with os.fdopen(os.open(pkf, os.O_WRONLY | os.O_CREAT, 0o600),
                       'w') as f:
            f.writelines(pk)
        with open(inventory_path, 'w') as f:
            log.info("Creating inventory file {0}".format(inventory_path))
            f.writelines(INVENTORY_TEMPLATE.substitute(
                {'master': host, 'user': user}))
        # Run the playbook
        cmd = "cd {0} && ansible-playbook -i inventory other.yml".format(
            repo_path)
        log.info("Running Ansible with command {0}".format(cmd))
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
        (out, err) = p.communicate()
        p_status = p.wait()
        log.info("Playbook stdout: %s\nstatus: %s" % (out, p_status))
        log.info("Deleting pk file {0} needed by Ansible".format(pkf))
        if not settings.DEBUG:
            shutil.rmtree(repo_path)
        return (p_status, out)

    def launch_app(self, provider, task, name, cloud_config,
                   app_config, user_data):
        """
        Handle the app launch process.

        This will:
        - Perform necessary checks and env setup, most notably create a new
          key pair.
        - Launch an instance and wait until ssh access can be established
        - Run an Ansible playbook to configure the instance
        """
        # Implicitly create a new KP for this instance
        # Note that this relies on the baseVMApp implementation!
        kp_name = "CL-" + "".join([c for c in name if c.isalpha() or
                                  c.isdigit()]).rstrip()
        app_config['config_cloudlaunch']['keyPair'] = kp_name
        # Launch an instance and check ssh connectivity
        result = super(CloudMan2AppPlugin, self).launch_app(
            provider, task, name, cloud_config, app_config,
            user_data=None)
        inst = provider.compute.instances.get(
            result.get('cloudLaunch', {}).get('instance', {}).get('id'))
        pk = result.get('cloudLaunch', {}).get('keyPair', {}).get('material')
        timeout = 0
        while (not self._check_ssh(inst.public_ips[0], pk=pk) or
               timeout > 200):
            log.info("Waiting for ssh on {0}...".format(inst.name))
            time.sleep(5)
            timeout += 5
        # Configure the instance
        task.update_state(
            state='PROGRESSING',
            meta={'action': 'Configuring container cluster manager.'})
        self._run_playbook(inst.public_ips[0], pk)
        result['cloudLaunch']['applicationURL'] = \
            'http://{0}:8080/'.format(result['cloudLaunch']['publicIP'])
        task.update_state(
            state='PROGRESSING',
            meta={'action': "Waiting for CloudMan to become ready at %s"
                  % result['cloudLaunch']['applicationURL']})
        self.wait_for_http(result['cloudLaunch']['applicationURL'])
        return result
