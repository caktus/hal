import os

from fabric.api import cd, env, get, hide, local, put, require, run, settings, sudo, task
from fabric.colors import red
from fabric.contrib import files, project
from fabric.utils import abort, error

# Notes:
#
# There are two users to be aware of here.
#
# 'hal': the user that Ibid runs under. It is not privileged, and cannot
#        sudo. env.project_user is set to this, and most provisioning and
#        deploying will override the default user and ssh as this user.
#        Your local user will need to have access to the `hal` user via
#        ssh key.
#
# you: your own user on the remote server, which you need ssh key access to,
#        and that does have 'sudo' access. When fabric needs to sudo, it'll
#        connect to the remote host using this user. If your local userid
#        is different than your remote userid, use the '-u' option on fabric
#        to tell Fabric your remote userid.



# This repo
env.repo = "git@github.com:caktus/hal"

# Put your production server settings into servers.py.
# Copy servers.py-example to servers.py and edit.
from servers import production_settings


@task
def local():
    env.hosts = ['localhost']
    env.botname = 'hal2'
    env.project_user = 'hal'
    setup_paths()

@task
def vagrant():
    # See README for how to test using vagrant
    env.hosts = ['localhost:2222']
    env.botname = 'vagrant'
    env.project_user = 'hal'
    env.repo = '/vagrant/hal'
    setup_paths()

@task
def production():
    # Settings are configured in servers.py in the
    # production_settings dictionary
    for key in production_settings:
        setattr(env, key, production_settings[key])
    setup_paths()

def setup_paths():
    env.root = os.path.join('/home', env.project_user)
    env.workdir = os.path.join(env.root, 'ibid-work')
    env.venv = os.path.join(env.root, 'ibid-venv')
    env.pip = os.path.join(env.venv, "bin/pip")
    # ibid's own logs
    env.log_dir = os.path.join(env.root, "ibid-logs")
    # logs from IRC messages
    env.irc_log_dir = os.path.join(env.root, "irc-logs")
    env.db_file = "%(workdir)s/ibid.db" % env
    env.database = "sqlite:///%(db_file)s" % env


def setup_pip():
    require('hosts', provided_by=['local', 'vagrant', 'production'])
    # Arrange for pip to use a cache so reprovisioning doesn't take forever
    with settings(user=env.project_user):
        pip_cache_dir = os.path.join(env.root, "pip-download-cache")
        if not files.exists(pip_cache_dir):
            run("mkdir %s" % pip_cache_dir)
        pip_conf_dir = os.path.join(env.root, ".pip")
        if not files.exists(pip_conf_dir):
            run("mkdir %s" % pip_conf_dir)
        pip_conf_file = os.path.join(pip_conf_dir, "pip.conf")
        ctx = {
            'cachedir': pip_cache_dir,
        }
        files.upload_template("pip-conf-template", pip_conf_file, context=ctx)


def pip(command):
    # Run pip, appending `command` as the rest of the command line
    run("%s %s" % (env.pip, command))


@task
def db_setup():
    require('hosts', provided_by=['local', 'vagrant', 'production'])
    with settings(user=env.project_user):
        with cd(env.workdir):
            if not files.exists("ibid.ini"):
                abort("need ibid.ini file before can setup db")
            if not files.exists(env.db_file):
                run(os.path.join(env.venv, "bin/ibid-db") + " --upgrade")

@task
def deploy():
    """Create or update everything on the server and start Ibid"""
    require('hosts', provided_by=['local', 'vagrant', 'production'])

    # Ubuntu/debian packages required by some plugins
    sudo("apt-get install -y fortunes fortune-mod units nmap ipcalc git-core python-virtualenv python-dev supervisor")

    # As the bot user:
    with settings(user=env.project_user):
        if files.exists(env.workdir):
            with cd(env.workdir):
                run("git pull")
        else:
            with cd(env.root):
                run("git clone %(repo)s %(workdir)s" % env)
        if not files.exists(env.venv):
            run("virtualenv --distribute --no-site-packages %(venv)s" % env)
        setup_pip()
        with cd(env.workdir):
            pip("install -Ur requirements/server.txt")

        run("mkdir -p %(log_dir)s" % env)
        run("mkdir -p %(irc_log_dir)s" % env)

        # Upload the ini files
        # have to use Jinja format because Ibid itself uses Python string format in the same file
        ini_file = os.path.join(env.workdir, "ibid.ini")
        files.upload_template("ibid.ini-template",
                              ini_file,
                              context=env,
                              use_jinja=True,
                              # template_dir must be set for Jinja - fabric bug, probably
                              template_dir=".")
        files.upload_template("logging.ini-template",
                              os.path.join(env.workdir, "logging.ini"),
                              context=env,
                              use_jinja=True,
                              # template_dir must be set for Jinja - fabric bug, probably
                              template_dir=".")

        # If no local.ini file on the server yet, and if there's one
        # here, copy it up, with substitutions.
        with cd(env.workdir):
            if os.path.exists("local.ini") and not files.exists("local.ini"):
                files.upload_template("local.ini",
                                      os.path.join(env.workdir, "local.ini"),
                                      context=env,
                                      use_jinja=True,
                                      template_dir=".")
            # Create database if it's not there already
            # Can't do this until the .ini files have been set up
            db_setup()

    # As ourselves (with sudo privileges):

    # Set up supervisor to run it
    files.upload_template("ibid_supervisord.conf-template",
                          "/etc/supervisor/conf.d/ibid.conf",
                          context=env,
                          use_sudo=True)
    sudo("supervisorctl reload")

    with settings(warn_only=True):
        stop()
    start()


@task
def stop():
    require('hosts', provided_by=['local', 'vagrant', 'production'])
    sudo("supervisorctl stop ibid")


@task
def start():
    require('hosts', provided_by=['local', 'vagrant', 'production'])
    sudo("supervisorctl start ibid")


@task
def restart():
    stop()
    start()

