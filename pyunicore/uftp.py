from ftplib import FTP
from pyunicore.client import Resource

'''
    Work in progress

    helpers for authenticating to a UFTP Auth server
'''


class UFTP(Resource):
    ''' authenticate UFTP transfers and use ftplib to interact with
        the UFTPD server
    '''
    uftp_session_tag = "___UFTP___MULTI___FILE___SESSION___MODE___"

    def __init__(self, transport, base_url):
        super(UFTP, self).__init__(transport, base_url)
        self.refresh()

    def refresh(self):
        self.site_urls = {}
        for entry in self.properties:
            try:
                self.site_urls[entry] = self.properties[entry]['href']
            except Exception as e:
                pass
            
    def access_info(self):
        return self.properties['client']

    def open_session(self, server_name=None, base_dir="", **kwargs):
        ''' open an FTP session at the given UFTP server
        If 'basedir' is not given, the user's home directory is the base dir.
        The ftplib FTP object is returned.
        '''
        if server_name is None:
            url = self.site_urls.values()[0]
        else:
            url = self.site_urls[server_name]
        req = {"serverPath": base_dir+self.uftp_session_tag}
        params = self.transport.post(url=url, json=req).json()
        port = params['serverPort']
        host = params['serverHost']
        pwd  = params['secret']
        ftp = FTP()
        ftp.connect(host,port)
        ftp.login("anonymous", pwd)
        return ftp

    def download(self, remote_file, destination=None, server_name=None, base_dir="", **kwargs):
        ''' download the given remote file, optionally renaming it '''
        ftp = self.open_session(server_name, base_dir)
        if destination is None:
            destination = os.path.basename(remote_file)
        ftp.retrbinary("RETR %s" % remote_file, open(destination, 'wb').write)
        ftp.close()


class Share(Resource):
    ''' UFTP Data Sharing helper '''

    ANONYMOUS = "CN=ANONYMOUS,O=UNKNOWN,OU=UNKNOWN"

    def __init__(self, transport, base_url):
        super(Share, self).__init__(transport, base_url)

    def share(self, path, user, access="READ"):
        ''' create or update a share '''
        req = {"path": path}
        req['access'] = access
        req['user'] = user
        res = self.transport.post(url=self.resource_url, json=req)
        return res.headers['Location']

