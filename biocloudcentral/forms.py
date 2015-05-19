from django import forms
from biocloudcentral import models


class DynamicChoiceField(forms.ChoiceField):
    """
    Override the ChoiceField to allow AJAX-populated choices in the part of the
    form.
    """
    def valid_value(self, value):
        # TODO: Add some validation code to ensure passed data is valid.
        # Return True if value is valid else return False
        return True


class CloudManForm(forms.Form):
    """
    Details needed to boot a setup and boot a CloudMan instance.
    """
    key_url = "https://aws-portal.amazon.com/gp/aws/developer/account/index.html?action=access-key"
    ud_url = "https://wiki.galaxyproject.org/CloudMan/UserData"
    target = "target='_blank'"
    textbox_size = "input_xlarge"
    cloud = forms.ModelChoiceField(queryset=models.Cloud.objects.all(),
                                   help_text="Choose from the available clouds. The credentials "
                                   "you provide below must match (ie, exist on) the chosen cloud.",
                                   widget=forms.Select(attrs={"class": "%s disableable" % textbox_size,
                                   "onChange": "get_dynamic_fields(this.options[this.selectedIndex].value)"}))
    access_key = forms.CharField(required=True,
                                 widget=forms.TextInput(attrs={"class": "%s disableable" % textbox_size}),
                                 help_text="Your cloud account access key. For the Amazon cloud, available from "
                                 "the <a href='{0}' {1} tabindex='-1'>security credentials page</a>.".format(
                                     key_url, target))
    secret_key = forms.CharField(required=True,
                                 widget=forms.TextInput(attrs={"class": "%s disableable" % textbox_size}),
                                 help_text="Your cloud account secret key. For the Amazon cloud, also available "
                                 "from the <a href='{0}' {1} tabindex='-1'>security credentials page</a>."
                                 .format(key_url, target))
    # A simple text input element
    # cluster_name = forms.CharField(required=True,
    #                                help_text="Name of your cluster used for identification and "
    #                                "relaunching. This can be any name you choose.",
    #                                widget=forms.TextInput(attrs={"class": textbox_size}))
    cluster_name = forms.CharField(required=True,
                                   help_text="Name of your cluster used for identification and "
                                   "relaunching. If creating a new cluster, type any name you like.",
                                   widget=forms.TextInput(attrs={"class": "%s disableable" % textbox_size,
                                    "type": "hidden", "placeholder": "Enter a NEW cluster name or fetch existing"}))
    # A simple drop down element
    # cluster_name = DynamicChoiceField((("", "Provide cloud credentials first"),),
    #                         help_text="Choose a previously existing "
    #                           "cluster or provide a new name for a new cluster.",
    #                         widget=forms.Select(attrs={"class": textbox_size}))
    password = forms.CharField(widget=forms.PasswordInput(render_value=False,
                                                          attrs={"class": textbox_size}),
                               help_text="Your choice of password, for the CloudMan "
                               "web interface and accessing the server via ssh.")
    instance_type = DynamicChoiceField((("", "Choose cloud type first"),),
                            help_text="Type (ie, virtual hardware configuration) of the server to start.",
                            widget=forms.Select(attrs={"class": textbox_size, 'disabled': 'disabled'}))
    placement = DynamicChoiceField((("", "Fill above fields & click refresh to fetch"),),
                            help_text="A specific placement zone where your server will run. This "
                            "requires you have filled out the previous 6 fields!",
                            required=False,
                            widget=forms.Select(attrs={"class": textbox_size, 'disabled': 'disabled'}))
    key_pair = DynamicChoiceField((("", "Fill above fields & click refresh to fetch"),),
                            help_text="A specific key pair to be used when launching your server. This "
                            "requires you have filled out the initial 6 fields!",
                            required=False,
                            widget=forms.Select(attrs={"class": textbox_size, 'disabled': 'disabled'}))
    bucket_default = forms.CharField(required=False,
                              label="Default bucket",
                              widget=forms.TextInput(attrs={"class": textbox_size}),
                              help_text="The default bucket to use. See <a href='{0}' {1} tabindex='-1'>"
                              "CloudMan's wiki</a> for a detailed description of this option."
                              .format(ud_url, target))
    post_start_script_url = forms.CharField(required=False,
                              label="Post-start script",
                              widget=forms.TextInput(attrs={"class": textbox_size}),
                              help_text="A URL to the post-start script. See <a href='{0}' {1} tabindex='-1'>"
                              "CloudMan's wiki</a> for a detailed description of this option."
                              .format(ud_url, target))
    worker_post_start_script_url = forms.CharField(required=False,
                              label="Worker post-start script",
                              widget=forms.TextInput(attrs={"class": textbox_size}),
                              help_text="A URL to the post-start script for worker nodes. See "
                              "<a href='{0}' {1} tabindex='-1'>CloudMan's wiki</a> for the description."
                              .format(ud_url, target))
    share_string = forms.CharField(required=False,
                              label="Shared cluster string",
                              widget=forms.TextInput(attrs={"class": textbox_size}),
                              help_text="A share string to use for deriving this cluster instance.")
    extra_user_data = forms.CharField(required=False,
                                label="Extra User-Data",
                                widget=forms.widgets.Textarea(attrs={"class": textbox_size}),
                                help_text="Pass advanced properties to CloudMan via the the cloud"
                                "infrastructure's user-data mechanism. Properties should be in YAML"
                                "formatted key-value pairs.")
    image_id = DynamicChoiceField((("", "Choose cloud type first"),),
                            help_text="The machine image to start (* indicates the default machine image).",
                            label="Image",
                            required=False,
                            widget=forms.Select(attrs={"class": textbox_size, 'disabled': 'disabled',
                            "onChange": "get_flavors(this.options[this.selectedIndex].value)"}))
    flavor_id = DynamicChoiceField((("", "Choose image first"),),
                            help_text="The flavor to use (* indicates the default flavor).",
                            label="Flavor",
                            required=False,
                            widget=forms.Select(attrs={"class": textbox_size, 'disabled': 'disabled'}))
    custom_image_id = forms.CharField(required=False,
                              label="Custom image ID",
                              widget=forms.TextInput(attrs={"class": textbox_size}),
                              help_text="Having selected 'Custom image' in the previous drop down,"
                              "provide desired maching image ID (e.g., ami-da5532cs)")
    institutional_email = forms.EmailField(required=False,
                                 widget=forms.TextInput(attrs={"class": "%s" % textbox_size}),
                                 help_text="Your institutional email. For grant-reporting purposes only.")

class FlavorAdminForm(forms.ModelForm):
    class Meta:
        model = models.Flavor
        widgets = {
            'user_data': forms.Textarea(attrs={'cols': 80, 'rows': 20}),
        }
