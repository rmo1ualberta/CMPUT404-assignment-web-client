#!/usr/bin/env python3
# coding: utf-8
# Copyright 2022 Abram Hindle, https://github.com/tywtyw2002, https://github.com/treedust, and Raymond Mo
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Do not use urllib's HTTP GET and POST mechanisms.
# Write your own HTTP GET and POST
# The point is to understand what you have to send and get experience with it

import sys
import socket
import re
# you may use urllib to encode data appropriately
import urllib.parse

TCP_PORT = 80
HTTP_VER = 'HTTP/1.1'

def help():
    print("httpclient.py [GET/POST] [URL]\n")

class HTTPResponse(object):
    def __init__(self, code=200, body=""):
        self.code = code
        self.body = body

class HTTPClient(object):
    #def get_host_port(self,url):

    def connect(self, host, port):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if port == None:            # if port isn't defined, default to TCP port 80
                port = 80
            self.socket.connect((host, port))
        except Exception as e:
            print(f'Failed to create and connect socket to host {host} at port {port}. {e}')
            sys.exit()
        print(f"Socket connected to {host} at port {port}.")
        return None

    def get_code(self, data):
        """Gets the status code from a message

        Args:
            data (str): The message to extract the status code from

        Returns:
            code (int): The status code
        """
        lines = data.splitlines()
        resLine = lines[0].split(' ')                 # split response line into array, e.g. ['HTTP/1.1', '301', 'Moved', 'Permanently\r\n'] 
        code = None
        for item in resLine:
            if item.isdigit():
                code = int(item)
                break
        
        if code == None:
            print("ERROR: Status code was not found in the response line")
            sys.exit(1)

        # ideally we check if the code is an actual HTTP status code
        
        return code


    def get_headers(self,data):
        # What use does this have????
        lines = data.splitlines()
        headerLines = lines[1:lines.index('')]
        headers = '\r\n'.join(headerLines)
        return headers

    def get_body(self, data):
        lines = data.splitlines()
        bodyLines = lines[lines.index('')+1:]
        body = '\r\n'.join(bodyLines)
        return body
    
    def sendall(self, data):
        self.socket.sendall(data.encode('utf-8'))
        
    def close(self):
        self.socket.close()

    # read everything from the socket
    def recvall(self, sock):
        buffer = bytearray()
        done = False
        while not done:
            part = sock.recv(1024)
            if (part):
                buffer.extend(part)
            else:
                done = not part
        return buffer.decode('utf-8')

    def parse_url(self, url):
        """Given the url, parses it using urllib.parse, and returns

        Args:
            url (str)): The URL string to be parsed

        Returns:
            host (str), port (int), path (str): Straightforward.
        """
        urlParsed = urllib.parse.urlparse(url)
        host = urlParsed.hostname
        port = urlParsed.port
        path = urlParsed.path
        
        return host, port, path

    def build_http_req(self, method, host, port, path, reqBody, query=''):
        """Builds a HTTP request message

        Args:
            method (str): The request method (e.g. GET, POST)
            host (str): The host name
            port (int): The port used to connect to the host
            path (str): The requested path
            reqBody (str, optional): The request message's entity body. Defaults to ''.

        Returns:
            reqMessage (str): The built HTTP request message
        """
        # build HTTP request message
        if method == "GET" and query != '':
            requestLine = f"{method} {path}{query} {HTTP_VER}\r\n"
        else:
            requestLine = f"{method} {path} {HTTP_VER}\r\n"

        reqHeaders = [
            f'Accept: */*',
            f'Connection: close',
            f'Content-Length: {self.utf8len(reqBody)}',
            f'Upgrade-Insecure-Requests: 1',        # HTTPS GANG
            f'Server: python'
        ]
        # for a cleaner looking host header
        if port == None:
            reqHeaders.append(f'Host: {host}')
        else:
            reqHeaders.append(f'Host: {host}:{port}')

        # add content-type if post
        if method == "POST":
            reqHeaders.append(f'Content-Type: application/x-www-form-urlencoded')
            
        reqMessage = requestLine + '\r\n'.join(reqHeaders) + '\r\n\r\n' + reqBody

        return reqMessage


    # deprecated: used urllib.parse.urlencode instead for handling of special characters
    def build_body(self, args):
        reqBody = ''
        n=1
        if args != None:
            for key in args.keys():
                reqBody += f'{key}={args[key]}'
                if n != len(args.keys()):          # if not the last key, append &
                    reqBody += '&'
                n += 1
        return reqBody

    def GET(self, url, args=None):
        """Handles sending GET requests

        Args:
            url (str): A URL to GET from
            args (dic, optional): Optional arguments to send as a query. Defaults to None.

        Returns:
            A HTTPResponse object containing the response code and body
        """
        host, port, path = self.parse_url(url)

        # build query if it exists
        query = ''
        if args != None:
            query = urllib.parse.urlencode(args)
            query = '?' + query

        if len(path) == 0:                          # for cases where / is not specified at the end
            path = '/'
        
        reqMessage = self.build_http_req('GET', host, port, path, '', query)
        print('\n\n'+reqMessage)
        
        # connect and send the request message
        self.connect(host, port)
        self.sendall(reqMessage)
        # receive the response
        recvData = self.recvall(self.socket)
        self.close()
        print(recvData)

        code = self.get_code(recvData)
        body = self.get_body(recvData)
        return HTTPResponse(code, body)

    def POST(self, url, args=None):
        """Handles sending POST requests

        Args:
            url (str): A URL to POST to
            args (dic, optional): Data that will be sent to the requested host. Defaults to None.

        Returns:
            A HTTPResponse object containing the response code and body
        """
        host, port, path = self.parse_url(url)
        

        # build the body 
        reqBody = ''
        if args != None:
            reqBody = urllib.parse.urlencode(args)


        reqMessage = self.build_http_req('POST', host, port, path, reqBody)
        
        # connect and send the request message
        self.connect(host, port)
        self.sendall(reqMessage)

        # receive the response
        recvData = self.recvall(self.socket)
        self.close()
        print(recvData)

        code = self.get_code(recvData)
        body = self.get_body(recvData)
        return HTTPResponse(code, body)

    def utf8len(self, s):
        """ Gets the length of a string in bytes.
        Ref: https://stackoverflow.com/questions/30686701/python-get-size-of-string-in-bytes

        Args:
            s (string): The string to get the length of

        Returns:
            The length of the given string in bytes
        """
        return len(s.encode('utf-8'))

    def command(self, url, command="GET", args=None):
        if (command == "POST"):
            return self.POST( url, args )
        else:
            return self.GET( url, args )
    
if __name__ == "__main__":
    client = HTTPClient()
    command = "GET"
    if (len(sys.argv) <= 1):
        help()
        sys.exit(1)
    elif (len(sys.argv) == 3):
        print(client.command( sys.argv[2], sys.argv[1] ))
    else:
        print(client.command( sys.argv[1] ))
