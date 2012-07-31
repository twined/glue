import os
from fabric.api import *

from django.conf import settings

if os.environ.get('DJANGO_SETTINGS_MODULE'):
    projectmodule = __import__(os.environ.get('DJANGO_SETTINGS_MODULE', ''))
    PROJECT_NAME = projectmodule.__name__
else:
    raise ImportError("DJANGO_SETTINGS_MODULE must be available in environment")

GLUE_SETTINGS = {
    'project_name': PROJECT_NAME,
    'project_group': 'web',
    'ssh_user': 'user',
    'ssh_host': 'host.net',
    'ssh_port': 30000,
    'prod': {
        'process_name': PROJECT_NAME,
        'db_name': "%s_prod" % PROJECT_NAME,
        'db_user': PROJECT_NAME,
        'db_pass': 'database password',
        'venv_root': '/sites/.virtualenvs',
        'venv_name': PROJECT_NAME,
        'project_base': '/sites/prod',
        'git_branch': '1.4',
        'memcached_enabled': False,
        'redis_enabled': False,
        'redis_key': '',
        'public_path': 'public',
        'media_path': 'media',
    },

    'staging': {
        'process_name': "%s_staging" % PROJECT_NAME,
        'db_name': "%s_staging" % PROJECT_NAME,
        'db_user': PROJECT_NAME,
        'db_pass': 'database password',
        'venv_root': '/sites/.virtualenvs',
        'venv_name': "%s_staging" % PROJECT_NAME,
        'project_base': '/sites/staging',
        'git_branch': '1.4',
        'memcached_enabled': False,
        'redis_enabled': False,
        'redis_key': '',
        'public_path': 'public',
        'media_path': 'media',
    }
}

temp_settings = getattr(settings, 'GLUE_SETTINGS', {})
USER_SETTINGS = dict(GLUE_SETTINGS.items() + temp_settings.items())
USER_SETTINGS['prod'] = dict(
    GLUE_SETTINGS['prod'].items() + USER_SETTINGS.get('prod', {}).items()
)
USER_SETTINGS['staging'] = dict(
    GLUE_SETTINGS['staging'].items() + USER_SETTINGS.get('staging', {}).items()
)
GLUE_SETTINGS = USER_SETTINGS
