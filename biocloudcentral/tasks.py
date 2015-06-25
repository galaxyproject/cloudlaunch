# import time
import yaml
import copy
import logging

from celery import task
from bioblend.cloudman.launch import CloudManLauncher

from biocloudcentral import models

log = logging.getLogger(__name__)


@task()
def add(x, y):
    """
    A task used during testing; adds two provided numbers
    """
    # time.sleep(5)
    # print "in add"
    return x + y


@task()
def fetch_clusters(cloud, a_key, s_key):
    """
    Given a cloud object and appropriate credentials, retrieve a list of
    clusters associated with the given account. Return a dict of clusters'
    persistent data.
    """
    cml = CloudManLauncher(a_key, s_key, cloud)
    return cml.get_clusters_pd()


@task()
def instance_state(cloud, a_key, s_key, instance_id):
    """
    Check on the state of an instance until and return the state.
    """
    if not instance_id:
        state = {'instance_state': "",
                 'public_ip': "",
                 'placement': "",
                 'error': "Missing instance ID, cannot check the state."}
        return state
    cml = CloudManLauncher(a_key, s_key, cloud)
    return cml.get_status(instance_id)


@task()
def run_instance(form):
    """
    Run a CloudBioLinux/CloudMan instance with current session credentials.
    """
    # Dev code only!
    # Useful when wanting to skip the instance launch process but contitnue the process
    # response = {}
    # response['cluster_name'] = form['cluster_name']
    # response['password'] = form['password']
    # response['cloud_name'] = form['cloud_name']
    # response['cloud_type'] = form['cloud_type']
    # response['access_key'] = form['access_key']
    # response['instance_type'] = form['instance_type']
    # response['image_id'] = models.Image.objects.get(pk=form['image_id']).image_id
    # response['error'] = None
    # response['sg_names'] = ['CloudMan']
    # response['kp_name'] = 'cm_kp'
    # response['kp_material'] = ''
    # response['instance_id'] = 'i-l0cal'
    # response['instance_ip'] = '127.0.0.1'
    # response['institutional_email'] = form.get('institutional_email', '')
    # return response
    # End dev code

    err_msg = None
    kernel_id = None
    ramdisk_id = None

    # Fetch images
    if form['image_id']:
        if form['image_id'] == '0':
            image_id = form['custom_image_id']
        else:
            image = models.Image.objects.get(pk=form['image_id'])
            image_id = image.image_id
            kernel_id = image.kernel_id if image.kernel_id != '' else None
            ramdisk_id = image.ramdisk_id if image.ramdisk_id != '' else None
    else:
        try:
            image = models.Image.objects.get(cloud=form['cloud'], default=True)
            image_id = image.image_id
            kernel_id = image.kernel_id if image.kernel_id != '' else None
            ramdisk_id = image.ramdisk_id if image.ramdisk_id != '' else None
        except models.Image.DoesNotExist:
            err_msg = "Cannot find an image to launch for cloud {0}".format(form['cloud'])
            log.error(err_msg)
            return False

    # Handle flavor data
    flavor = None
    if form['flavor_id']:
        try:
            flavor = models.Flavor.objects.get(pk=form['flavor_id'])
        except ValueError:
            err_msg = "Could not find flavor {0}. Ignoring...".format(form['flavor_id'])
            log.warn(err_msg)
    elif not form.get('custom_image_id', None):  # Custom images have no flavors
        flavor = None
        try:
            flavor = models.Flavor.objects.get(image=image.pk, default=True)
        except models.Flavor.DoesNotExist:
            log.debug("No default flavor specified for image {0}. Ignoring...".format(image))
        except Exception, exc:
            err_msg = "Exception fetching flavor: {0}".format(exc)
            log.warn(err_msg)
    # Complement the form data with what's defined in the flavor
    if flavor and flavor.user_data:
        for key, value in yaml.load(flavor.user_data).iteritems():
            # Allow user-provided default bucket to override one specified in the flavor
            if key == 'bucket_default' and form.get('bucket_default', None):
                pass
            if key == 'initial_cluster_type' and form.get('initial_cluster_type', None):
                pass
            if key == 'galaxy_data_option' and form.get('galaxy_data_option', None):
                pass
            if key == 'pss' and form.get('pss', None):
                pass
            else:
                form[key] = value

    # Handle extra_user_data after flavor data so that flavor data can be overridden
    extra_user_data = form['extra_user_data']
    if extra_user_data:
        for key, value in yaml.load(extra_user_data).iteritems():
            form[key] = value
    del form['extra_user_data']

    instance_type = form['instance_type']
    # Create cloudman connection with provided creds
    cml = CloudManLauncher(form["access_key"], form["secret_key"], form['cloud'])
    form["freenxpass"] = form["password"]

    # Compose kwargs from form data making sure the named arguments are not included
    kwargs = copy.deepcopy(form)
    # key_name is the parameter name for the key pair in the launch method so
    # ensure it's there as a kwarg if provided in the form
    if form.get('key_pair', None):
        kwargs['key_name'] = form['key_pair']
    for key in form.iterkeys():
        if key in ['cluster_name', 'image_id', 'instance_type', 'password',
                   'placement', 'access_key', 'secret_key', 'cloud', 'key_pair']:
            del kwargs[key]

    response = {}
    if not err_msg:
        log.debug("Launching cluster {0} from image {1} on instance {2} in zone '{3}'."
                  .format(form['cluster_name'], image_id, instance_type, form['placement']))
        response = cml.launch(cluster_name=form['cluster_name'],
                              image_id=image_id,
                              instance_type=instance_type,
                              password=form["password"],
                              kernel_id=kernel_id,
                              ramdisk_id=ramdisk_id,
                              placement=form['placement'],
                              **kwargs)
    # Keep these parts of the form as part of the response
    response['cluster_name'] = form['cluster_name']
    response['password'] = form['password']
    response['cloud_name'] = form['cloud_name']
    response['cloud_type'] = form['cloud_type']
    response['access_key'] = form['access_key']
    response['instance_type'] = form['instance_type']
    response['institutional_email'] = form.get('institutional_email', '')
    response['image_id'] = image_id
    response['error'] = err_msg
    return response
