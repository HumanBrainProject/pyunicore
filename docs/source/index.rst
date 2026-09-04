Welcome to PyUNICORE
====================

`UNICORE <https://www.unicore.eu>`_ (**UN**\ iform **I**\ nterface to
**CO**\ mputing **RE**\ sources) offers a ready-to-run system
including client and server software.  It makes distributed computing
and data resources available in a seamless and secure way in intranets
and the internet.

PyUNICORE is a Python library providing an API for UNICORE's
`REST API <https://unicore-docs.readthedocs.io/en/latest/user-docs/rest-api>`_ ,
making common tasks like file access, job submission and management,
workflow submission and management more convenient, and integrating
UNICORE features better with typical Python usage.

PyUNICORE is based on the 'httpx' HTTP client library and offers both
synchronous and asynchronous APIs.

PyUNICORE comes with a commandline utility 'unicore', which is modeled
after the UNICORE Commandline Client (UCC) and supports many of UCC's
features.

In addition, this library contains code for using
`UFTP <https://uftp-docs.readthedocs.io>`_ (UNICORE FTP),
a UFTP driver for `PyFilesystem <https://github.com/PyFilesystem/pyfilesystem2>`_
and a UNICORE implementation of a
`Dask Cluster <https://distributed.dask.org/en/stable/>`_

This project has received funding from the European Union’s
Horizon 2020 Framework Programme for Research and Innovation under the
Specific Grant Agreement Nos. 720270, 785907 and 945539
(Human Brain Project SGA 1, 2 and 3)

PyUNICORE is Open Source under the :ref:`BSD License <license>`,
the source code is on `GitHub <https://github.com/HumanBrainProject/pyunicore>`_.


Installation
------------

Install from PyPI with

.. code:: console

    pip install -U pyunicore

Additional extra packages may be required for your use case:

 * Creating JWT tokens signed with keys requires the "cryptography" package
 * Using UFTP with pyfilesystem requires "fs"


You can install (one or more) extras with pip:

.. code:: console

    pip install -U pyunicore[crypto]


.. toctree::
	:maxdepth: 2
	:caption: Using PyUNICORE

	basic_usage
	async_client
	authentication
	uftp
	dask
	port_forwarding
	CLI


.. toctree::
	:maxdepth: 1
	:caption: Links

	license
