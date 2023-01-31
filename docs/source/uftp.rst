UFTP
----

`UFTP (UNICORE FTP) <https://uftp-docs.readthedocs.io>`_ is a fast file transfer toolkit,
based on the standard FTP protocol, with an added authentication layer based on UNICORE.

To make a UFTP connection, a user first needs to authenticate to an
authentication service, which will produce a one-time password, which is
then used to connect to the actual UFTP file server.

UFTP support in PyUNICORE is based on the `ftplib <https://docs.python.org/3/library/ftplib.html>`_
standard library.

Basic UFTP usage
~~~~~~~~~~~~~~~~

Opening an FTP session involves authenticating to an authentication service using
UNICORE credentials. Depending on the authentication service, different credentials
might be accepted.

Here is a basic example using username/password.

.. code:: python

  import pyunicore.credentials as uc_credentials
  import pyunicore.uftp as uc_uftp

  # URL of the authentication service
  auth_url = "https://localhost:9000/rest/auth/TEST"

  # remote base directory that we want to access
  base_directory = "/data"

  # authenticate with username/password
  credential = uc_credentials.UsernamePassword("demouser", "test123")

  uftp_session = uc_uftp.UFTP().connect(credential, auth_url, base_directory)

The object returned by `connect()` is an `ftplib` `FTP` object.



Using UFTP for PyFilesystem
~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can create a `PyFilesystem <https://github.com/PyFilesystem/pyfilesystem2>`_
`FS` object either directly in code, or implicitely via a URL.

The convenient way is via URL:

.. code:: python

  from fs import open_fs
  fs_url = "uftp://demouser:test123@localhost:9000/rest/auth/TEST:/data"
  uftp_fs = open_fs(fs_url)


The URL format is

.. code:: console

    uftp://[username]:[password]@[auth-server-url]:[base-directory]?[token=...][identity=...]


The FS driver supports three types of authentication

  * Username/Password - give `username` and `password`
  * SSH Key - give `username` and the `identity` parameter,
    where `identity` is the filename of a private key.
    Specify the `password` if needed to load the private key
  * Bearer token - give the token value via the `token` parameter


(note: the SSH key authentication using this library requires
UFTP Auth server 2.7.0 or later)

Mounting remote filesystems via UFTP
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

PyUNICORE contains a FUSE driver based on `fusepy <https://pypi.org/project/fusepy>`_,
allowing you to mount a remote filesystem via UFTP. Mounting is a two step process,

  * authenticate to an Auth server, giving you the UFTPD host/port and one-time password
  * run the FUSE driver

The following code example gives you the basic idea:

.. code:: python

  import pyunicore.client as uc_client
  import pyunicore.credentials as uc_credentials
  import pyunicore.uftp as uc_uftp
  import pyunicore.uftpfuse as uc_fuse

  _auth = "https://localhost:9000/rest/auth/TEST"
  _base_dir = "/opt/shared-data"
  _local_mount_dir = "/tmp/mount"

  # authenticate
  cred = uc_credentials.UsernamePassword("demouser", "test123")
  _host, _port, _password  = uc_uftp.UFTP().authenticate(cred, _auth, _base_dir)

  # run the fuse driver
  fuse = uc_fuse.FUSE(
  uc_fuse.UFTPDriver(_host, _port, _password), _local_mount_dir, foreground=False, nothreads=True)
