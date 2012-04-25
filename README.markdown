This package contains a fabfile (+ cuisine) for simple provisioning and deployment of Django app running on Debian 6.

The stack is:

* Nginx
* Gunicorn
* Django
* Memcached
* Postgresql

Supervisord is optional. Right now I personally just restart guncorn using a kill -HUP. This seems to work fine for my purposes. I've included an example init script in the provision folder.

## Usage

Install the requirements:

    pip install -r requirements.txt

Set up your settings.py file.

Initialize your server

    fab initialize

Provision it

    fab provision

Deploy!

    fab deploy


## Settings

    TODO