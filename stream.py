#!/usr/bin/env python
import os
import http.server
import time
import threading
from urllib.parse import urlparse
from cheapmp3 import CheapMP3

root = os.getcwd() +"/"
cach_dir = root + 'cache/'


class AP(http.server.BaseHTTPRequestHandler):
    #protocol_version = "HTTP/1.1"
    t = 0

    def __init__(self, request, client_address, server):
        super().__init__(request,client_address,server)

    def response(self,code,headers):
        self.send_response(code)
        for hk in headers:
            self.send_header(hk,headers[hk])
        self.end_headers()

    def get_root(self):
        return urlparse(self.path)

    def set_time(self,t):
        self.t = t
    def get_time(self):
        return self.t

    def send_head(self,samplerate=48000,channels=2,bitrate=96):
        heads = {'Cache-Control': 'no-cache, no-store',
                'Connection':'Close','Content-type':'audio/mpeg',
                'ice-audio-info':'samplerate=%d;channels=%d;bitrate=%d'%(samplerate,channels,bitrate),
                'icy-description':'Python test icy service',
                'icy-br': '%d'%bitrate,
                'icy-genre': 'K-pop',
                'icy-metadata': '1',
                'icy-name':'PyListen',
                'icy-pub': '0',
                'icy-url': 'http://www.549.ipdisk.co.kr',
                'Server': 'Icecast 2.4.0-kh10'
                }
        self.response(200,heads)

    def do_GET(self):
        return False
        
    #def log_message(self, format, *args):
    #    return

class HTTPMulitThread(http.server.HTTPServer):
    
    mp3 = None
    index = 0
    tindex = -1 # 적용 인덱스
    buff = None
    clients = []
    request_queue_size = 10

    def __init__(self, server_address, RequestHandlerClass,mp3):
        super().__init__(server_address, RequestHandlerClass)
        if not self.mp3:
            self.mp3 = CheapMP3(root+mp3)
            self.mp3.ReadFile()
            self.time = time.time()
            print("MP3 File!")
        self.thread = threading.Thread(target=self.load_buff)
        self.thread.daemon = True
        self.thread.start()
    
    def load_buff(self):
        while True:
            if int(self.time) < int(time.time()) - 0.5:
                self.time = time.time()
                self.buff = self.mp3.WriteFile(40,self.index * 40)
                print(len(self.buff),self.index)
                self.index += 1
                if self.index >= self.mp3.mNumFrames:
                    self.index = 0

    def service_actions(self):
        for i in range(len(self.clients)):
            ap = self.clients[i]
            if ap.get_time() !=self.time:
                ap.set_time(self.time)
                try:
                    ap.wfile.write(self.buff)
                except Exception as e:
                    print("연결끊김!", e)
                    self.clients.pop(i)
                    i -= 1
                    break

    def process_request(self, request, client_address):
        ap = AP(request, client_address, self)
        parsed_path=urlparse(ap.get_root().path)
        try:
            if parsed_path.path == "/stream":
                ap.send_head(44100)
                if ap.headers['Accept'] == "*/*" and "Range" in ap.headers:
                    self.clients.append(ap)
                    print("사용자 접속:" ,client_address)
                    return
                else :
                    print("헤더요청 처리")
                    pass
            else :
                ap.response(200,{'Content-type':'text/html'})
                ap.wfile.write("???".encode("UTF-8"))
        except Exception as e:
            print(e)
        self.shutdown_request(request)

if __name__ == "__main__":
    port = 8000
    server=HTTPMulitThread(("",port),AP,"Playlist - The Best Songs- 50 Songs.mp3")
    server.request_queue_size = 10
    server.serve_forever()
    server.RequestHandlerClass.clean_mem(server.RequestHandlerClass)


"""
ParseResult(scheme='', netloc='', path='/stream', params='', query='', fragment='')
<__main__.AP object at 0x048B7DD8>
Cache-Control: max-age=0
Upgrade-Insecure-Requests: 1
Sec-Fetch-User: ?1
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3
Sec-Fetch-Site: none
Sec-Fetch-Mode: navigate
Accept-Encoding: gzip, deflate, br
Accept-Language: ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7


127.0.0.1 - - [04/Dec/2019 02:26:36] "GET /stream HTTP/1.1" 200 -
ParseResult(scheme='', netloc='', path='/stream', params='', query='', fragment='')
<__main__.AP object at 0x048B7EE0>
Accept-Encoding: identity;q=1, *;q=0
Accept: */*
Sec-Fetch-Site: same-origin
Sec-Fetch-Mode: no-cors
Referer: http://localhost:8080/stream
Accept-Language: ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7
Range: bytes=0-
"""
