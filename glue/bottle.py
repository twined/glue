#!/usr/bin/env python
import os
import random

from fabric.api import *
from fabric.contrib.files import exists as _exists
from fabric.context_managers import settings as _settings, shell_env
from fabric.colors import red, green, yellow, cyan
from fabric.operations import prompt
from fabric.utils import abort


VERSION_NUMBER = '1.0.1'


def _get_version():
    return VERSION_NUMBER


def showconfig():
    """
    Prints out the config
    """
    require('hosts')
    import pprint
    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(env)


def syncdb():
    """
    Synchronize database models
    """
    require('hosts')
    print(cyan('-- syncdb // synchronizing db'))
    with cd(env.path):
        sudo('FLAVOR=%s %s/bin/python manage.py syncdb --noinput' % (
            env.flavor, env.venv_path), user=env.project_user)


def migrate():
    """
    Run database migrations
    """
    require('hosts')
    print(cyan('-- migrate // running db migrations'))
    with cd(env.path):
        sudo('FLAVOR=%s %s/bin/python manage.py migrate --noinput' % (
            env.flavor, env.venv_path), user=env.project_user)


def collectstatic():
    """
    Collect static for django application.
    """
    require('hosts')
    if env.flavor in ('prod', 'staging',):
        with cd(env.path):
            print '-- collectstatic // collecting static files for app'
            sudo('FLAVOR=%s %s/bin/python manage.py collectstatic --noinput' % (
                env.flavor, env.venv_path), user=env.project_user)


def update():
    """
    Updates app with newest source code, clears caches, and restarts gunicorn
    """
    require('hosts')
    with cd(env.path):
        gitpull()
        collectstatic()
        restart()

        if env.redis_enabled:
            print(cyan('-- redis // increasing cache generation key'))
            redis_increase_gen()

        if env.memcached_enabled:
            flushmemcached()


def mkvirtualenv():
    """
    Setup a fresh virtualenv.
    """
    require('hosts')
    print(cyan('-- mkvirtualenv // uploading bash_profile...'))
    put('conf/.bash_profile_source', '/home/%s/.bash_profile' % env.project_user, use_sudo=True)
    print(cyan('-- mkvirtualenv // setting owner and permissions 660'))
    _setowner(os.path.join('/home', env.project_user, '.bash_profile'))
    _setperms('660', os.path.join('/home', env.project_user, '.bash_profile'))
    print(cyan('-- mkvirtualenv // running virtualenvwrapper.sh'))
    sudo('export WORKON_HOME=/sites/.virtualenvs', user=env.project_user)
    with shell_env(WORKON_HOME='/sites/.virtualenvs'):
        sudo('source /usr/local/bin/virtualenvwrapper.sh', user=env.project_user)
    print(cyan('-- mkvirtualenv // chmoding hook.log to avoid permission trouble'))
    with _settings(warn_only=True):
        _setperms('660', os.path.join(env.venv_root, 'hook.log'))
        _setowner(os.path.join(env.venv_root, 'hook.log'))
    with _settings(warn_only=True):
        if _exists(env.venv_path):
            print(yellow('-- mkvirtualenv // virtualenv %s already exists - now removing.' % env.venv_path))
            sudo('export WORKON_HOME=/sites/.virtualenvs && source /usr/local/bin/virtualenvwrapper.sh && rmvirtualenv %s' % env.venv_name, user=env.project_user)
    sudo('export WORKON_HOME=/sites/.virtualenvs && source /usr/local/bin/virtualenvwrapper.sh && mkvirtualenv %s' % env.venv_name, user=env.project_user)


def upload_secrets():
    """
    Uploads secrets.cfg
    """
    print(cyan('-- upload_secrets // uploading secrets.cfg...'))
    put('%s/conf/env/secrets.cfg' % env.project_name, '%s/%s/conf/env/secrets.cfg' % (env.path, env.project_name), use_sudo=True)
    print(cyan('-- upload_secrets // chowning...'))
    _setowner(os.path.join(env.path, env.project_name, 'conf/env/secrets.cfg'))
    print(cyan('-- upload_secrets // chmoding'))
    _setperms('660', os.path.join(env.path, env.project_name, 'conf/env/secrets.cfg'))


def upload_virtualenv_vendors():
    """
    Uploads virtualenv vendors
    """
    if not _exists(os.path.join(env.venv_path, 'node_modules')):
        print(cyan('-- upload_virtualenv_vendors // uploading node_modules'))
        put('vendors/virtualenv/node_modules', '%s/' % env.venv_path, use_sudo=True)
        print(cyan('-- upload_virtualenv_vendors // chowning...'))
        _setowner(os.path.join(env.venv_path, 'node_modules'))
        print(cyan('-- upload_virtualenv_vendors // chmoding'))
        _setperms('770', os.path.join(env.venv_path, 'node_modules'))


def bootstrap():
    """
    Bootstraps and provisions project on host
    """
    require('hosts')
    _warn('''
        This is a potientially dangerous operation. Make sure you have\r\n
        all your ducks in a row, and that you have checked the configuration\r\n
        files both in conf/ and in the fabfile.py itself!
    ''')
    _confirmtask()
    createuser()
    deploy()
    mkvirtualenv()
    upload_virtualenv_vendors()
    upload_secrets()
    installreqs()
    createdb()
    supervisorcfg()
    nginxcfg()
    logrotatecfg()
    syncdb()
    migrate()
    collectstatic()
    gitpull()
    flushdb()
    loaddata()
    restart()
    _success()


def _warn(str):
    """
    Outputs a warning formatted str
    """
    print(red('-- WARNING ---------------------------------------'))
    print(red(str))
    print(red('-- WARNING ---------------------------------------'))


def restart():
    """
    Restarts the gunicorn process through supervisorctl
    """
    require('hosts')
    with cd(env.path):
        print(cyan('-- supervisor // restarting gunicorn process'))
        sudo('supervisorctl restart %s' % env.procname)


def stop():
    """
    Stops the gunicorn process through supervisorctl
    """
    require('hosts')
    with cd(env.path):
        print(cyan('-- supervisor // stopping gunicorn process'))
        sudo('supervisorctl stop %s' % env.procname)


def start():
    """
    Starts the gunicorn process through supervisorctl
    """
    require('hosts')
    with cd(env.path):
        print(cyan('-- supervisor // starting gunicorn process'))
        sudo('supervisorctl start %s' % env.procname)


def _setperms(perms, path):
    """
    chmods path to perms, recursively
    """
    if not perms:
        abort('_setperms: not enough arguments. perms=%s, path=%s' % (perms, path))
    if not path:
        abort('_setperms: not enough arguments. perms=%s, path=%s' % (perms, path))

    require('hosts')
    print(cyan('-- setperms // setting %s on %s [recursively]' % (perms, path)))
    sudo('chmod -R %s "%s"' % (perms, path))


def _setowner(path=''):
    """
    chowns provided path to project_user:project_group
    """
    if not path:
        abort('_setowner: cannot be empty')
    require('hosts')
    print(cyan('-- setowner // owning %s [recursively]' % path))
    sudo('chown %s:%s -R "%s"' % (env.project_user, env.project_group, path))


def syncmedia():
    """
    Synchronizes local and remote media directories. Potentially messy.
    """
    require('hosts')
    _confirmtask()
    with cd(env.path):
        _setperms('a+r', env.media_path)
        fixprojectperms()
        _setperms('g+w', env.public_path)
        rsync_command = r"""rsync -av -e 'ssh -p %s' %s@%s:%s %s""" % (
            env.port,
            env.user, env.host,
            env.media_path.rstrip('/') + '/',
            'public/media'
        )
        #print(red(rsync_command))
        print(cyan('-- syncmedia // syncing from server to local'))
        print local(rsync_command, capture=False)

        rsync_command = r"""rsync -av /sites/%s/public/media/ -e 'ssh -p %s' %s@%s:%s""" % (
            env.project_user,
            env.port,
            env.user, env.host,
            env.media_path.rstrip('/') + '/'
        )

        print(cyan('-- syncmedia // syncing from local to server'))
        print local(rsync_command, capture=False)

        _setowner(env.public_path)


def nukemedia():
    """
    Deletes public/media path recursively on host, then recreates
    directory and sets perms
    """
    require('hosts')
    print(red('-- WARNING ---------------------------------------'))
    print(red('You are about to delete %s from the remote server.' % env.media_path))
    print(red('command: rm -rf %s' % env.media_path))
    print(red('-- WARNING ---------------------------------------'))
    _confirmtask()
    print(cyan('-- nukemedia // ok, deleting files.'))
    sudo('rm -rf %s' % env.media_path)
    print(cyan('-- nukemedia // recreating media directory'))
    sudo('mkdir -p %s' % env.media_path, user=env.project_user)
    _setowner(env.media_path)
    _setperms('g+w', env.media_path)


def putdata():
    """
    Grabs a json dump of local dev database and uploads it to server
    """
    require('hosts')
    print local('FLAVOR=dev ./manage.py dumpdata > fixtures/application_db.json', capture=False)
    _setperms('g+w', '%s/fixtures' % env.path)
    put('fixtures/application_db.json', '%s/fixtures/application_db.json' % env.path, use_sudo=True)
    _setowner(env.media_path)


def flushdb():
    """
    Flush all data from database. Does not drop tables, only data.
    """
    require('hosts')
    print(red('-- WARNING ---------------------------------------------------------'))
    print(red('You are about to wipe the db from the remote %s server.' % env.flavor))
    print(red('db: %s' % env.db_name))
    print(red('-- WARNING ---------------------------------------------------------'))
    print("")
    _confirmtask()
    with cd(env.path):
        print(cyan('-- flushdb // flushing database'))
        sudo('FLAVOR=%s %s/bin/python manage.py sqlflush | psql %s' % (env.flavor, env.venv_path, env.db_name), user=env.project_user)


def loaddata():
    """
    Loads fixtures/application_db.json into database
    """
    require('hosts')
    print(red('-- WARNING ---------------------------------------------------------'))
    print(red('You are about to load the %s db with fixtures. This could destroy your db.' % env.flavor))
    print(red('db: %s' % env.db_name))
    print(red('-- WARNING ---------------------------------------------------------'))
    print("")
    _confirmtask()
    with cd(env.path):
        print(cyan('-- loaddata // loading fixtures'))
        sudo('FLAVOR=%s %s/bin/python manage.py loaddata fixtures/application_db.json' % (env.flavor, env.venv_path), user=env.project_user)


def importfixtures():
    """
    Loads the fixture from fixtures/application_db.json into database.
    WARNING: this resets the db!
    """
    require('hosts')
    with cd(env.path):
        flushdb()
        loaddata()
        #sudo('FLAVOR=%s %s/bin/python manage.py migrate --noinput' % (env.flavor, env.venv_path), user=env.project_user)

WORDLIST_PATHS = [os.path.join('/', 'usr', 'share', 'dict', 'words')]
DEFAULT_MESSAGE = "Are you sure you want to do this?"
WORD_PROMPT = '  [%d/%d] Type "%s" to continue (^C quits): '


def _confirmtask(msg=DEFAULT_MESSAGE, horror_rating=1):
    """Prompt the user to enter random words to prevent doing something stupid."""

    valid_wordlist_paths = [wp for wp in WORDLIST_PATHS if os.path.exists(wp)]

    if not valid_wordlist_paths:
        abort('No wordlists found!')

    with open(valid_wordlist_paths[0]) as wordlist_file:
        words = wordlist_file.readlines()

    print msg

    for i in range(int(horror_rating)):
        word = words[random.randint(0, len(words))].strip()
        p_msg = WORD_PROMPT % (i + 1, horror_rating, word)
        answer = prompt(p_msg, validate=r'^%s$' % word)


def gitpull():
    """
    Pulls latest commit from git, and resets permissions/owners
    """
    require('hosts')
    with cd(env.path):
        print(cyan('-- git // git pull, to make sure we are still at HEAD'))
        sudo('git pull', user=env.project_user)

    fixprojectperms()


def fixprojectperms():
    """
    Chowns the project directory to project_user:project_group
    """
    require('hosts')
    _setowner(env.path)
    logrotatecfg()


def _success():
    print(green('----------------------------------------------------'))
    print(green('-- twined // All tasks finished!'))


def tailgun(follow=''):
    """
    Tail the Gunicorn log file.
    """
    require('hosts')

    with cd(env.path):
        if follow:
            run('tail -f logs/gunicorn.log')
        else:
            run('tail logs/gunicorn.log')


def supervisorcfg():
    """
    Links our supervisor config file to the config.d dir
    """
    require('hosts')
    print(cyan('-- supervisorcfg // linking config file to conf.d/'))
    if not _exists('/etc/supervisor/conf.d/%s.conf' % (env.procname)):
        sudo('ln -s %s/conf/supervisord/%s.conf /etc/supervisor/conf.d/%s.conf' % (env.path, env.flavor, env.procname))
    else:
        print(yellow('-- supervisorcfg // %s.conf already exists!' % (env.procname)))

    sudo('supervisorctl reread')
    sudo('supervisorctl update')


def nginxcfg():
    """
    Links our nginx config to the sites-enabled dir
    """
    require('hosts')
    print(cyan('-- nginxcfg // linking config file to conf.d/'))
    if not _exists('/etc/nginx/sites-enabled/%s' % (env.procname)):
        sudo('ln -s %s/conf/nginx/%s.conf /etc/nginx/sites-enabled/%s' % (env.path, env.flavor, env.procname))
    else:
        print(yellow('-- nginxcfg // %s already exists!' % env.procname))
    print(cyan('-- nginxcfg // make sure our log directories exist!'))
    if not _exists('%s/logs/nginx' % env.path):
        sudo('mkdir -p %s/logs/nginx' % env.path, user=env.project_user)
    else:
        print(yellow('-- nginxcfg // %s/logs already exists!' % (env.path)))
    print(cyan('-- nginxcfg // reloading nginx config'))
    sudo('/etc/init.d/nginx reload')


def logrotatecfg():
    """
    Links our logrotate config file to the config.d dir
    """
    require('hosts')
    logrotate_src = "%s/etc/logrotate/%s.conf" % (env.path, env.flavor)
    print(cyan('-- logrotateconf // linking config file to conf.d/'))
    if not _exists('/etc/logrotate.d/%s.conf' % (env.procname)):
        sudo('ln -s %s /etc/logrotate.d/%s.conf' % (logrotate_src, env.procname))
    else:
        print(yellow('-- logrotateconf // %s.conf already exists!' % (env.procname)))

    # set permission to 644
    print(cyan('-- setperms // setting logrotate conf to 644'))
    sudo('chmod %s "%s"' % (perms, logrotate_src))

    # set owner to root
    print(cyan('-- setowner // setting logrotate owner to root'))
    sudo('chown root:wheel "%s"' % logrotate_src)


def createuser():
    """
    Creates a linux user on host, if it doesn't already exists
    and adds is to configured group
    """
    require('hosts')
    with _settings(warn_only=True):
        output = sudo('id %s' % env.project_user)
        if output.failed:
            # no such user, create it.
            sudo('adduser %s' % env.project_user)
            sudo('usermod -a -G %s %s' % (env.project_group, env.project_user))
            output = sudo('id %s' % env.project_user)
            if output.failed:
                abort('createuser: ERROR: could not create user!')
        else:
            print(yellow('-- createuser // user %s already exists.' % env.project_user))
        print(cyan('-- createuser // add to group'))
        sudo('usermod -a -G %s %s' % (env.project_group, env.project_user))


def createdb():
    """
    Creates pgsql role and database
    """
    require('hosts')
    with _settings(warn_only=True):
        print(cyan('-- createdb // creating user %s' % env.db_user))
        result = sudo('psql -c "CREATE USER %s WITH NOCREATEDB NOCREATEUSER ENCRYPTED PASSWORD \'%s\';"' % (env.db_user, env.db_pass), user='postgres')
        if result.failed:
            if 'already exists' in result:
                print(yellow('-- createdb // user already exists'))
            else:
                abort(red('-- createdb // error in user creation!'))

        print(cyan('-- createdb // creating db %s with owner %s' % (env.db_name, env.db_user)))
        result = sudo('psql -c "CREATE DATABASE %s WITH OWNER %s ENCODING \'UTF-8\'";' % (
            env.db_name, env.db_user), user='postgres')

        if result.failed:
            if 'already exists' in result:
                print(yellow('-- createdb // database already exists'))
            else:
                abort(red('-- createdb // error in db creation!'))


def deploy():
    """
    Clone the git repository to the correct directory
    """
    require('hosts')
    if not _exists(env.path):
        print(cyan('-- creating %s as %s' % (env.path, env.project_user)))
        sudo('mkdir -p %s' % env.path, user=env.project_user)
        with cd(env.path):
            if (getattr(env, 'branch', '') == ''):
                print(cyan('-- git // cloning source code into %s' % env.path))
                sudo('git clone file:///code/git/%s .' % env.repo, user=env.project_user)
            else:
                print(cyan('-- git // cloning source code branch %s into %s' % (env.branch, env.path)))
                sudo('git clone file:///code/git/%s -b %s .' % (env.repo, env.branch), user=env.project_user)
        fixprojectperms()
    else:
        print(cyan('-- directory %s exists, skipping git clone & updating instead' % env.path))
        gitpull()

def clear():
    """
    Deletes the project directory
    """


def installreqs():
    "Install the required packages from the requirements file using pip"
    require('hosts')
    with cd(env.path):
        sudo('export WORKON_HOME=/sites/.virtualenvs && source /usr/local/bin/virtualenvwrapper.sh && workon %s && pip install -r ./requirements/%s.pip' % (
            env.venv_name, env.flavor), user=env.project_user)


def flushmemcached():
    "Flush memcached"
    print(cyan('-- memcached // flushing cache'))
    run('echo flush_all | nc 127.0.0.1 11211')


def redis_increase_gen():
    "Increase redis global gen key"
    # run ./manage.py incr_gen?
    # run('echo INCR %s | nc 127.0.0.1 6379' % env.redis_key)


def nginxreload():
    "Reloads nginxs configuration"
    print(cyan('-- nginx // reloading'))
    sudo('/etc/init.d/nginx reload')


def nginxrestart():
    "Restarts nginxs configuration"
    print(cyan('-- nginx // restarting'))
    sudo('/etc/init.d/nginx restart')


def searchreindex():
    "Rebuild Haystack search index"
    require('hosts')
    with cd(env.path):
        print(cyan('-- searchreindex // rebuilding haystack index'))
        sudo("%s/bin/python manage.py rebuild_index" % env.venv_path, user=env.project_user)
