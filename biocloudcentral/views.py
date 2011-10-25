"""Base views.
"""
from django.http import HttpResponse
from django import forms
from django.shortcuts import render, redirect

import logging
import boto
from boto.ec2.regioninfo import RegionInfo
from boto.exception import EC2ResponseError

log = logging.getLogger(__name__)

# ## Landing page with redirects

def home(request):
    launch_url = request.build_absolute_uri("/launch")
    if launch_url.startswith(("http://127.0.0.1", "http://localhost")):
        return redirect("/launch")
    else:
        return redirect("https://biocloudcentral.herokuapp.com/launch")

# ## CloudMan launch and configuration entry details

class CloudManForm(forms.Form):
    """Details needed to boot a setup and boot a CloudMan instance.
    """
    cluster_name = forms.CharField(required=True,
                                   help_text="Name of your cluster used for identification. "
                                   "This can be any name you choose.")
    password = forms.CharField(widget=forms.PasswordInput(render_value=False),
                               help_text="Password used to access the CloudMan web interface "
                               "and your instance via ssh and FreeNX.")
    access_key = forms.CharField(required=True,
                                 help_text="Your Amazon Access Key ID. Available from "
                                 "the security credentials page.")
    secret_key = forms.CharField(required=True,
                                 help_text="Your Amazon Secret Access Key. Also available "
                                 "from the security credentials page.")
    instance_type = forms.ChoiceField((("m1.large", "Large"),
                                       ("t1.micro", "Micro"),
                                       ("m1.xlarge", "Extra Large")),
                                      help_text="Amazon instance type to start.")

def launch(request):
    """Configure and launch CloudBioLinux and CloudMan servers.
    """
    if request.method == "POST":
        form = CloudManForm(request.POST)
        if form.is_valid():
            print form.cleaned_data
            ec2_conn = connect_ec2(form.cleaned_data['access_key'], form.cleaned_data['secret_key'])
            sg_name = create_cm_security_group(ec2_conn)
            kp_name = create_key_pair(ec2_conn)
            rs = run_instance(ec2_conn=ec2_conn, \
                              instance_type=form.cleaned_data['instance_type'], \
                              key_name=kp_name, \
                              security_groups=[sg_name])
            if rs is not None:
                return HttpResponse('Started an instance with ID %s and IP <a href="http://%s/cloud" target="_blank">%s</a>' \
                    % (rs.instances[0].id, rs.instances[0].public_dns_name, rs.instances[0].public_dns_name))
            else:
                return HttpResponse('A problem starting an instance. Check AWS console.')
    else:
        form = CloudManForm()
    return render(request, "launch.html", {"form": form})

# ## Cloud interaction methods
def connect_ec2(a_key, s_key):
    """ Create and return an EC2 connection object.
    """
    # Use variables for forward looking flexibility
    # AWS connection values
    region_name = 'us-east-1'
    region_endpoint = 'ec2.amazonaws.com'
    is_secure = True
    ec2_port = None
    ec2_conn_path = '/'
    r = RegionInfo(name=region_name, endpoint=region_endpoint)
    ec2_conn = boto.connect_ec2(aws_access_key_id=a_key,
                          aws_secret_access_key=s_key,
                          is_secure=is_secure,
                          region=r,
                          port=ec2_port,
                          path=ec2_conn_path)
    return ec2_conn

def create_cm_security_group(ec2_conn, sg_name='CloudMan'):
    """ Create a security group with all authorizations required to run CloudMan.
        If the group already exists, check its rules and add the missing ones.
        Return the name of the created security group.
    """
    cmsg = None
    # Check if this security group already exists
    sgs = ec2_conn.get_all_security_groups()
    for sg in sgs:
        if sg.name == sg_name:
            cmsg = sg
            log.debug("Security group '%s' already exists; will add authorizations next." % sg_name)
            break
    # If it does not exist, create security group
    if cmsg is None:
        log.debug("Creating Security Group %s" % sg_name)
        cmsg = ec2_conn.create_security_group(sg_name, 'A security group for CloudMan')
    # Add appropriate authorization rules
    # If these rules already exist, nothing will be changed in the SG
    ports = (('80', '80'), # Web UI
             ('20', '21'), # FTP
             ('22', '22'), # ssh
             ('30000', '30100'), # FTP transfer
             ('42284', '42284')) # CloudMan UI
    for port in ports:
        try:
            if not rule_exists(cmsg.rules, from_port=port[0], to_port=port[1]):
                cmsg.authorize(ip_protocol='tcp', from_port=port[0], to_port=port[1], cidr_ip='0.0.0.0/0')
            else:
                log.debug("Rule (%s:%s) already exists in the SG" % (port[0], port[1]))
        except EC2ResponseError, e:
            log.error("A problem with security group authorizations: %s" % e)
    # Add rule that allows communication between instances in the same SG
    g_rule_exists = False # Flag to indicate if group rule already exists
    for rule in cmsg.rules:
        for grant in rule.grants:
            if grant.name == cmsg.name:
                g_rule_exists = True
                log.debug("Group rule already exists in the SG")
        if g_rule_exists:
            break
    if g_rule_exists is False: 
        try:
            cmsg.authorize(src_group=cmsg)
        except EC2ResponseError, e:
            log.error("A problem w/ security group authorization: %s" % e)
    log.info("Done configuring '%s' security group" % cmsg.name)
    return cmsg.name

def rule_exists(rules, from_port, to_port, ip_protocol='tcp', cidr_ip='0.0.0.0/0'):
    """ A convenience method to check if an authorization rule in a security
        group exists.
    """
    for rule in rules:
        if rule.ip_protocol == ip_protocol and rule.from_port == from_port and \
           rule.to_port == to_port and cidr_ip in [ip.cidr_ip for ip in rule.grants]:
            return True
    return False

def create_key_pair(ec2_conn, key_name='cloudman_key_pair'):
    """ Create a key pair with the provided name.
        Return the name of the key or None if there was an error creating the key. 
    """
    kp = None
    # Check if a key pair under the given name already exists. If it does not,
    # create it, else return.
    kps = ec2_conn.get_all_key_pairs()
    for akp in kps:
        if akp.name == key_name:
            kp = akp
            log.debug("Key pair '%s' already exists; not creating it again." % key_name)
            return kp.name
    try:
        kp = ec2_conn.create_key_pair(key_name)
    except EC2ResponseError, e:
        log.error("Problem creating key pair '%s': %s" % (key_name, e))
        return None
    # print kp.material # This should probably be displayed to the user on the screen and allow them to save the key?
    log.info("Created key pair '%s'" % kp.name)
    return kp.name

def run_instance(ec2_conn, instance_type, image_id='ami-ad8e4ec4', kernel_id=None, ramdisk_id=None,
                 key_name='cloudman_key_pair', security_groups=['CloudMan']):
    """ Start an instance. If instance start was OK, return the ResultSet object
    else return None.
    """
    rs = None
    rs = ec2_conn.run_instances(image_id=image_id,
                                instance_type=instance_type,
                                key_name=key_name,
                                security_groups=security_groups,
                                kernel_id=kernel_id,
                                ramdisk_id=ramdisk_id)
    try:
        if rs:
            log.info("Started an instance with ID %s" % rs.instances[0].id)
        else:
            log.warning("Problem starting an instance?")
    except Exception, e:
        log.error("Problem starting an instance: %s" % e)
    return rs
