import os
import git
from fabric.api import cd, env, prefix, run, sudo, abort
from cuisine import mode_user, dir_ensure, user_ensure, group_ensure, \
                    file_append, mode_sudo, group_user_ensure, file_upload, \
                    ssh_authorize, file_attribs, package_ensure, file_link, \
                    file_exists

from settings import *

# app details
env.app = APP_NAME
env.repo = APP_REPO
env.branch = APP_REPO_BRANCH
env.static_root = DJANGO_STATIC_ROOT
env.media_root = DJANGO_MEDIA_ROOT

# directory containing provisioning files
env.provision_dir = 'provision'
# base project dir (dir of this fabfile by default)
env.local_dir = os.path.dirname(env.real_fabfile)

# remote host(s)
env.hosts = APP_HOSTS
# remote user/group to log in as (created in initialize)
env.remote_user = REMOTE_USER
env.remote_group = REMOTE_GROUP

# the root dir of this repo (the dir of this fabfile)
env.root_dir = os.path.join('/srv/', env.app)
# path to the virtualenv
env.virtualenv = os.path.join(env.root_dir, 'shared/env')
env.activate = 'source %s/bin/activate ' % env.virtualenv
env.app_dir = os.path.join(env.root_dir, env.app)
# django media root: /current/myapp/media
env.media_dir = os.path.join(env.root_dir, 'current', env.app, 'media')


def initialize():
    """Log in to the server as root and create the initial user/group"""
    env.user = 'root'
    mode_user()
    group_ensure(env.remote_group)
    user_ensure(env.remote_user, shell='/bin/bash')
    group_user_ensure(env.remote_user, env.remote_group)

    # copy local public key to user's authorized_keys for convenience
    if os.path.exists('~/.ssh/id_rsa.pub'):
        f = open('~/.ssh/id_rsa.pub', 'rb')
        ssh_authorize(env.remote_user, f.read())
        f.close()

    file_append("/etc/sudoers", "%(remote_user)s   ALL=(ALL) NOPASSWD:ALL\n" % env)


def provision():
    """Sets up packages and the deploy tree"""
    mode_sudo()

    for p in DEBIAN_PACKAGES:
        package_ensure(p)

    # Create the deploy tree
    dir_ensure("/srv", owner="root", group="root")
    ensure_tree('/srv', DEPLOY_TREE, owner=env.remote_user, group=env.remote_group)

    # Postgres
    dir_ensure("/etc/postgresql/8.4/main", owner="postgres", group="postgres")
    provision_file_upload("/etc/postgresql/8.4/main/pg_hba.conf", mode='644')
    provision_file_upload("/etc/postgresql/8.4/main/postgresql.conf", mode='644')

    # nginx
    provision_file_upload("/etc/nginx/nginx.conf", mode='644', owner='root', group='root')
    provision_file_upload("/etc/nginx/sites-available/%(app)s" % env, mode='644', owner='root', group='root')
    file_link("/etc/nginx/sites-available/%(app)s" % env, "/etc/nginx/sites-enabled/%(app)s" % env)

    # set up the virtualenv
    if not file_exists(env.virtualenv):
        sudo('easy_install pip')
        sudo('pip install virtualenv')
        run('sudo -u %(remote_user)s virtualenv %(virtualenv)s' % env, pty=True)

    # gunicorn
    dir_ensure("/etc/gunicorn", owner="root", group="root")
    provision_file_upload("/etc/gunicorn/%(app)s.conf.py" % env, mode='644', owner='root', group='root')

    # supervisord
    provision_file_upload("/etc/supervisor/conf.d/%(app)s.conf" % env, mode='644', owner='root', group='root')

    # app init script
    provision_file_upload("/etc/init.d/%(app)s" % env, mode='755', owner="root", group="root")

    # poor man's start on boot
    provision_file_upload("/etc/rc.local", mode='755', owner="root", group="root")

    # settings_local.py
    provision_file_upload("/srv/%(app)s/shared/settings_local.py", owner=env.remote_user, group=env.remote_group)


def deploy():
    """
    Push code, sync, migrate, generate media, restart
    """
    assert_git_valid()

    with cd(env.root_dir):
        with prefix(env.activate):
            # clone the latest repo
            if file_exists("_latest"):
                abort("deploy halted: remove dead _latest clone")
            run("git clone -b %(branch)s %(repo)s releases/_latest" % env)

            # link settings_local.py
            # TODO: handle template
            file_link("/srv/%(app)s/shared/settings_local.py", "/srv/%(app)s/releases/_latest/%(app)s/settings_local.py" % env)

            # get the latest release
            env.latest_release = run("git --git-dir=releases/_latest/.git rev-parse origin/%(branch)s" % env)

            # pip install requirements
            output = run("pip install -r releases/_latest/requirements.txt")
            if output.failed:
                abort('deploy halted: pip install failed!')

            # migrate
            output = run("python releases/_latest/%(app)s/manage.py migrate" % env)
            if output.failed:
                abort('deploy halted: migration failed!')

            # collectstatic
            file_link("/srv/%(app)s/shared/%(static_root)s" % env, "releases/_latest/%(app)s/%(static_root)s" % env)
            output = run('python releases/_latest/%(app)s/manage.py collectstatic --noinput -i "*.pyc"' % env)
            if output.failed:
                abort('deploy halted: collectstatic failed!')

            # swap symlinks
            run("mv releases/_latest releases/%(latest_release)s" % env)
            if file_exists("current"):
                if file_exists("previous"):
                    run("rm previous")
                run("mv current previous")

            # link current to latest release
            file_link("/srv/%(app)s/releases/%(latest_release)s" % env, "current")

            # restart supervisord
            # TODO: there must be a better way
            #sudo('supervisorctl status %(app)s | sed "s/.*[pid ]\([0-9]\+\)\,.*/\\1/" | xargs kill -HUP' % env)

            # restart gunicorn
            sudo('/etc/init.d/%(app)s restart')


def rollback():
    # TODO
    # roll forward with hotfixes for now ;)
    pass


# Helper functions

def ensure_tree(root, tree, **kwargs):
    """ Recursively ensure a directory tree """
    for dr, subtree in tree.items():
        current_root = os.path.join(root, dr)
        dir_ensure(current_root, **kwargs)
        ensure_tree(current_root, subtree, **kwargs)


def provision_file_upload(path, **kwargs):
    """ Find the file in the deploy dir, upload it and set attributes """
    f = os.path.join(env.local_path, env.provision_dir, env.role, path[1:])
    if not os.path.exists(f):
        abort('Local file not found: %s' % f)
    file_upload(path, f)
    file_attribs(path, **kwargs)


def assert_git_valid():
    """
    Check git repo to make sure it is ready to deploy the latest code
    """
    repo = git.Repo(env.local_dir)

    # check the branch, repo and untracked files
    if repo.active_branch.name != env.branch:
        raise Exception('You must be in %(branch)s to deploy' % env)
    elif repo.is_dirty():
        raise Exception('Directory not clean, you must commit.')
    elif repo.untracked_files:
        raise Exception('There are untracked files: %s' % repo.untracked_files)

    # TODO: check that remote repo is up to date
    # TODO: check that local copy is up to date
