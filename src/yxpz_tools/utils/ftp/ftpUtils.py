import os
from ftplib import FTP

class ftpUtils:
    def __init__(self):
        self.HOST = ''
        self.PORT = 21
        self.USER = ''
        self.PASS = ''

    def upload(self,local,remote_dir= '/'):
        if not os.path.exists(local):
            raise FileNotFoundError(f'{local} does not exist')
        ftp = FTP()
        ftp.connect(host=self.HOST,port=self.PORT,timeout=30)
        ftp.login(self.USER,self.PASS)
        print(f'Connected to {ftp.host}:{ftp.port}')
        if remote_dir and remote_dir != '/':
            for d in remote_dir.strip("/").split("/"):
                try:
                    ftp.cwd(d)
                except Exception:
                    ftp.mkd(d)
                    ftp.cwd(d)
        fname = os.path.basename(local)
        with open(local,'rb') as f:
            ftp.storbinary('STOR ' + fname, f) #二进制上传
        print('上传成功')
        ftp.quit()
        return True
    def upload_bytes(self,file_bytes,remote_dir= '/'):
        ''' 文件以文件流的方法上传'''
        #@TODO
        pass
