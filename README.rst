Caktus IBID: Hal
================

This repository (github.com/caktus/hal) is used by Caktus to run an
IRC bot named "hal".  The underlying software is Ibid.

What is Ibid
------------

Ibid is a bot. We're using it primarily as an IRC bot, though it has
the ability to work with other kinds of networks too.

Home page: https://launchpad.net/ibid/
Latest doc: http://ibid.omnia.za.net/docs/trunk/index.html

Server prep
-----------

Before using this, you'll need an Ubuntu-like server, with at least
two users defined, one that will run the bot, and the other used when
deploying.

The bot user, which we call ``hal``, should be a normal user, without
sudo privileges, for safety's sake.

The other user account is for the person who'll be deploying.  That user
account should have sudo privileges on the server.

The person deploying should have ssh public key access to both of these
users on the server.

Directories and files
---------------------

These are under ``/home/hal``, or the home directory of whatever user
is running the bot:

* ``ibid-work``: work dir for running Ibid.  This has configuration files,
  and is the current dir when running Ibid. This does _not_ have
  Ibid source; that's installed in the `ibid-venv` virtual environment.
  It _might_ contain source for custom plugins, though.
  This is a clone of the github.com/caktus/hal repository, plus some
  additional files that are set up at deploy time.
* ``ibid-venv``: virtual environment used to run Ibid. This is where all the
  dependencies are installed, _as well as_ ibid itself.
* ``ibid-irclogs``: Logs from IRC traffic
* ``ibid-logs``: Logs from Ibid itself

Deploying
---------

You'll do all this work on your local system, not the server. We use
fabric to control the server.

* Clone this repo locally::

    git clone git@github.com:caktus/hal

* Start a virtualenv::

    mkvirtualenv --distribute hal

* Install the requirements for deploying::

    cd hal
    pip install -r requirements/deploy.txt

* For each file named ``*-example``, make a copy without the ``-example``
  and edit following the comments inside.

  local.ini will have your IRC config - which server to connect to,
  which channels to join, etc.

  servers.py will have your local server info - the server name where
  you'll run ibid, the user name it should run as, etc.

* Deploy::

    fab [envname] deploy

  where `envname` is ``local``, or ``vagrant``, or ``production``.

There's one thing you'll need to do on the server now. Login as hal,
cd to the ibid-work directory, activate the virtualenv, and run
ibid-setup. Follow the prompts and it will let you set up an account
that you can use to admin the bot::

    ssh hal@servername
    . ibid-venv/bin/activate
    cd ibid-work
    ibid-setup

There's more about Ibid auth and credentials below.

Running Ibid
------------

Ibid is kept running by ``supervisor``, with config file at
``/etc/supervisor/conf.d/ibid_supervisord.conf``. You can control
it from your local system::

    fab [envname] stop
    fab [envname] start
    fab [envname] restart

Sources
-------

In Ibid, a ``source`` is one network and place where people have
identities. A source could be a particular IRC network, or a
jabber server, or any of a number of other options.

Basically, a ``source`` is one domain that Ibid connects to and
interacts with the users there.

In our setup, sources are configured in the local.ini file.

Auth and credentials within Ibid
---------------------------------

An ``identity`` is a userid on a source.  E.g. IRC nick ``dpoirier``
on IRC server caktus is one identity, while IRC nick ``dpoirier`` on
IRC server freenode would be a different identity.

An ``account`` represents a particular person. Both dpoirier on
caktus IRC and dpoirier on freenode might be associated with
the same account (but they don't have to be).

Use ``create account [<name>]`` to create a new account.

Associate an account with an identity using
``link user <accountname> to <identity> on <source>``

``Credentials`` are ways that an identity can prove that they
are entitled to access as a particular account. For example, an account
might have a ``password`` credential, and if an identity (a user on
an IRC server) can provide that credential, they might be able to
access things that that account is allowed to access.

To set a password use
``authenticate <account> [on source] using <method> [<credential>]``
with <method> set to ``password`` and <credential> the password to set.

.. warning::

   Do **not** use a valuable password for Ibid. When you set it or authenticate
   with it, it **will** end up in the logs on the server and might end up
   visible to others.

To "login" you first need to be connected using an identity associated with
an account. Then tell hal ``auth <password>``.

If you need to create a new account without going through Ibid (maybe you
forgot the admin's password), just login to the server, activate the venv,
cd to the work directory, and run ``ibid-setup`` again. Follow the prompts
to create a new account using a new nick. Then connect to IRC with that
nick, auth to Ibid, and you're ready to do whatever you need.

Vagrant
-------

To test using vagrant, create users for Ibid and yourself on the vagrant
system just like any other server, clone this repository as `hal` inside your
vagrant working directory (next to Vagrantfile), then use the ``vagrant``
env name with fabric, e.g. ``fab vagrant deploy``.

Useful commands
---------------

lsmod
    list installed modules or plugins
help <modulename>
    list features provided by that module
(help|how do I use) <command>
    provide help on <command>
reload
    reload things
reread config
    read the config file again
