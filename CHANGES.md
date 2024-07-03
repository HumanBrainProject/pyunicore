Changelog for PyUNICORE
=======================

Issue tracker: https://github.com/HumanBrainProject/pyunicore

Version 1.1.0 (mmm dd, 2024)
----------------------------
 - API CHANGE: new Storage.put_file() method accepting
   str-like or file-like data to upload to a remote destination
 - new feature: new pyfilesystem implementation "uftpmount" which mounts
   the remote directory and then accesses it via the local FS (OSFS)

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
