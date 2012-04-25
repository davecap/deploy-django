APP_NAME = 'myapp'
APP_REPO = 'git@github.com:GITUSER/myapp.git'
APP_REPO_BRANCH = 'master'

APP_HOSTS = ['deploy@myapp.com']
REMOTE_USER, REMOTE_GROUP = 'deploy', 'deploy'

DJANGO_STATIC_ROOT = 'static_root'
DJANGO_MEDIA_ROOT = 'media_root'

DEBIAN_PACKAGES = [
    "sudo",
    "libpq-dev",
    "python-dev",
    "swig",
    "rsync",
    "wkhtmltopdf",
    "memcached",
    "nginx",
    "denyhosts",
    "screen",
    "vim",
    "imagemagick",
    "openssl",
    "postgresql",
    "postfix",
    "git",
    "python-setuptools",
    "supervisor"
]

DEPLOY_TREE = {
    APP_NAME: {
        'releases': {},
        'shared': {
            'logs': {},
            'media_root': {},
            DJANGO_STATIC_ROOT: {}
        }
    }
}