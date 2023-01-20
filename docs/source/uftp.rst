UFTP
----

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

.. code::python

  import pyunicore.client as uc_client
  import pyunicore.credentials as uc_credentials
  import pyunicore.uftp as uc_uftp
  import pyunicore.uftpfuse as uc_fuse

  _auth = "https://localhost:9000/rest/auth/TEST"
  _base_dir = "/opt/shared-data"
  _local_mount_dir = "/tmp/mount"

  # authenticate
  cred = uc_credentials.UsernamePassword("demouser", "test123")
  uftp = uc_uftp.UFTP(uc_client.Transport(cred), _auth, _base_dir)
  _host, _port, _password  = uftp.authenticate()

  # run the fuse driver
  fuse = uc_fuse.FUSE(
  uc_fuse.UFTPDriver(_host, _port, _password), _local_mount_dir, foreground=False, nothreads=True)
