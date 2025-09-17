Port forwarding / tunneling
---------------------------

Opens a local server socket for clients to connect to, where traffic
gets forwarded to a service on a HPC cluster login (or compute) node.
This feature requires UNICORE 9.1.0 or later on the server side.

You can use this feature in two ways

 * in your own applications via the ``pyunicore.client.Job`` class.
 * you can also open a tunnel from the command line using the ``pyunicore.forwarder`` module

Here is an example for a command line tool invocation:

.. code:: console

  LOCAL_PORT=4322
  JOB_URL=https://localhost:8080/DEMO-SITE/rest/core/jobs/some_job_id
  REMOTE_PORT=8000
  python3 -m pyunicore.forwarder --token <your_auth_token> \
     -L $LOCAL_PORT \
     $JOB_URL/forward-port?port=$REMOTE_PORT \


Your application can now connect to ``localhost:4322`` but all traffic
will be forwarded to port 8000 on the HPC login node where your application
is running.

See

.. code:: console

  python3 -m pyunicore.forwarder --help

for all options.

If you want to tunnel to a compute node, you need to specify the compute node in your command line:

.. code:: console

  LOCAL_PORT=4322
  JOB_URL=https://localhost:8080/DEMO-SITE/rest/core/jobs/some_job_id
  REMOTE_PORT=8000
  COMPUTE_NODE=cnode1234
  python3 -m pyunicore.forwarder --token <your_auth_token> \
     -L $LOCAL_PORT \
     $JOB_URL/forward-port?port=$REMOTE_PORT?host=$COMPUTE_NODE \


If the remote UNICORE server is 10.2.1 or later, it is also supported to connect to a UNIX domain socket
file on a login node. This is usually preferable for security reasons. The domain socket file must be in the
UNICORE job working directory. To connect, simply specify the domain socket filename like so:

.. code:: console

  LOCAL_PORT=4322
  SOCKET_FILE=sock
  JOB_URL=https://localhost:8080/DEMO-SITE/rest/core/jobs/some_job_id
  python3 -m pyunicore.forwarder --token <your_auth_token> \
     -L $LOCAL_PORT \
     $JOB_URL/forward-port?file=$SOCKET_FILE \

Again, this will only work if the job is running on a login node.
