Changelog for PyUNICORE
=======================

Issue tracker: https://github.com/HumanBrainProject/pyunicore


Version 1.3.1 (May 15, 2025)
----------------------------
 - fix: allow single-valued extra options for the FUSE driver

Version 1.3.0 (May 12, 2025)
----------------------------
 - new feature: CLI: implemented more authentication options
   (oidc-agent, oidc-server, anonymous)
 - new feature: CLI: 'info' command

Version 1.2.0 (Nov 08, 2024)
----------------------------

 - UFTP FUSE driver: add '--read-only' option
 - New feature: commandline client script 'unicore' with a number
   of commands modeled after the 'ucc' commandline client
 - fix: the Job.working_dir function was hanging in case the working
   directory could not be created

Version 1.1.1 (Oct 01, 2024)
----------------------------
 - fix: type annotations did not work on Python3.7

Version 1.1.0 (Sep 30, 2024)
----------------------------
 - API CHANGE: new Storage.put_file() method accepting
   str-like or file-like data to upload to a remote destination
 - new feature: new pyfilesystem implementation "uftpmount" which mounts
   the remote directory and then accesses it via the local FS (OSFS)
 - fix: make sure job working directory is ready for use (fixes a
   potential race condition with UNICORE 10.1)

Version 1.0.1 (Mar 22, 2024)
----------------------------
 - fix: setting transport preferences immediately and automatically
   "takes effect" without requiring additional action by the
   user of the class

Version 1.0.0 (Feb 23, 2024)
----------------------------
 - after many 0.x releases in the course of the Human Brain Project,
   we decided to finally call it "1.0.0"
 - for a full list of releases, see
   https://pypi.org/project/pyunicore/#history
