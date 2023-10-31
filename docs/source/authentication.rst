Authentication
--------------

PyUNICORE supports all the authentication options available for
UNICORE, so you can use the correct one for the server that you
are trying to access.

Basic authentication options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The classes for the supported authentication options
are in the `pyunicore.credentials` package.


Username and password
^^^^^^^^^^^^^^^^^^^^^

.. code:: python

  import pyunicore.credentials as uc_credentials
  
  # authenticate with username/password
  credential = uc_credentials.UsernamePassword("demouser", "test123")

This will encode the supplied username/password and add it as an
HTTP header ``Authorization: Basic ...`` to outgoing calls.


Bearer token (OAuth/OIDC)
^^^^^^^^^^^^^^^^^^^^^^^^^

This will add the supplied token as an HTTP header 
``Authorization: Bearer ...`` to outgoing calls.

.. code:: python

  import pyunicore.credentials as uc_credentials
  
  # authenticate with Bearer token
  token = "..."
  credential = uc_credentials.OIDCToken(token)

Basic token
^^^^^^^^^^^

This will add the supplied value as a HTTP header 
``Authorization: Basic ...`` to outgoing calls.

.. code:: python

  import pyunicore.credentials as uc_credentials
  
  # authenticate with Bearer token
  token = "..."
  credential = uc_credentials.BasicToken(token)

JWT Token
^^^^^^^^^

This is a more complex option that creates a JWT token that is signed
with a private key - for example this is usually an authentication option
supported by the UFTP Authserver. In this case the user's UFTP / SSH key is
used to sign.

The simplest way to create this credential is to use the
`create_credential()` helper function.

.. code:: python

  import pyunicore.credentials as uc_credentials
  
  # authenticate with SSH key
  uftp_user  = "demouser"
  identity_file = "~/.uftp/id_uftp"
  credential = uc_credentials.create_credential(
  			username = uftp_user,
  			identity = identity_file)


The ``JWTToken`` credential can also be used for "trusted services",
where a service uses its server certificate to sign the token. Of
course this must be enabled / supported by the UNICORE server.

Anonymous access
^^^^^^^^^^^^^^^^

If for some reason you explicitly want anonymous calls, i.e. NO authentication
(which is treated differently from having invalid credentials!),
you can use the ``Anonymous`` credential class:

.. code:: python

  import pyunicore.credentials as uc_credentials
  
  # NO authentication
  credential = uc_credentials.Anonymous()

This can be useful for simple health checks and the like.

User preferences (advanced feature)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If the user mapping at the UNICORE server gives you access to more than
one remote user ID or primary group, you can select one using the 
`user preferences <https://unicore-docs.readthedocs.io/en/latest/user-docs/rest-api/index.html#user-preferences>`_
feature of the UNICORE REST API.

The `access_info()` method shows the result of authentication
and authorization.

.. code:: python

  import json
  import pyunicore.client as uc_client
  import pyunicore.credentials as uc_credentials
  
  credential = uc_credentials.UsernamePassword("demouser", "test123")
  base_url = "https://localhost:8080/DEMO-SITE/rest/core"
  client = uc_client.Client(credential, base_url)

  print(json.dumps(client.access_info(), indent=2)

You can get access to the user preferences via the ``Transport`` object that every
PyUNICORE resource has.

For example, to select a primary group (from the ones that are available)

.. code:: python

  client = uc_client.Client(credential, base_url)
  client.transport.preferences = "group:myproject1"

Note that (of course) you cannot select a UID/group that is not available, trying that
will cause a 403 error.


Creating an authentication token (advanced feature)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For some use cases (like automated workflows) you might want to not store your actual
credentials (like passwords or private keys) for security reasons. For this purpose, you
can use your (secret) credentials to have the UNICORE server issue a (long-lived)
authentication token, that you can then use for your automation tasks without worrying
that your secret credentials get compromised.

Note that you still should keep this token as secure as possible, since it would allow
anybody who has the token to authenticate to UNICORE with the same permissions and
authorization level as your real credentials.

You can access the
`token issue endpoint <https://unicore-docs.readthedocs.io/en/latest/user-docs/rest-api/index.html#creating-a-token>`_
using the PyUNICORE client class:

.. code:: python

  client = uc_client.Client(credential, base_url)
  my_auth_token = client.issue_auth_token(lifetime  = 3600,
                                          renewable = False,
                                          limited   = True)

and later use this token for authentication:

.. code:: python

  import pyunicore.credentials as uc_credentials
  
  credential = uc_credential.create_token(token=my_auth_token)
  client = uc_client.Client(credential, base_url)

The parameters are
 * ``lifetime`` : token lifetime in seconds
 * ``renewable``: if True, the token can be used to issue a new token
 * ``limited``  : if True, the token is only valid for the server that issued it. 
   If False, the token is valid for all UNICORE servers that the 
   issuing server trusts, i.e. usually those that are in the same UNICORE Registry
