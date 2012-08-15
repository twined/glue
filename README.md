GLUE
=====

**NOTE: This is tailored for the twined project structure, it probably won't work too well without customization on other project bootstraps.**

Installation:
-------------

    pip install -e git://github.com/twined/glue.git#egg=glue-dev

Add `glue` to `INSTALLED_APPS` in your `conf/settings.py`

**GLUE** keeps its config in a `GLUE_SETTINGS` dictionary, which you can override in your settings file. A couple of settings are mandatory, so this is the minimal config:

    # glue settings
    GLUE_SETTINGS = {
        'ssh_user': 'username',
        'ssh_host': 'host.net',
        'ssh_port': 30000,
        'prod': {
            'db_pass': 'prod_password',
        },
        'staging': {
            'db_pass': 'staging_password',
        }
    }

Take a look at `glue/settings.py` for the complete settings dict.

DJANGO_SETTINGS_MODULE:
-----------------------
**GLUE** needs to access your `DJANGO_SETTINGS_MODULE` environment var,
you can set it in your virtualenv's `postactivate` hook:

    export DJANGO_SETTINGS_MODULE=yourproject.path.to.settings

The `postactivate` hook can be found in your virtualenv's `bin/` dir.

Management command:
-------------------

**`./manage.py build_fabfile > filename`**

creates a fabfile.py named *filename*.
