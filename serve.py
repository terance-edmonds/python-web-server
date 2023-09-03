import socket
import sys
import glob
import subprocess
import json
import urllib.parse
import os
from threading import Thread

# server configs
HOST='localhost'
PORT=2728
FILE_DIR='htdocs'
BUFFER_SIZE=8192 # 8KB

# socket server
server = None

# content types for different file extensions
# along with an execute type
content_types_file = open('content-types.json')
content_types = json.load(content_types_file)

def formatRequest(client_socket):
    # get data from http client request (max 1KB)
    # format into a string
    request = client_socket.recv(1024).decode('utf-8')

    if not request:
        return [None, None]

    # split the request string into lines
    lines = request.split('\r\n')
    # get the first line and split by space
    data = lines[0].split()

    method = data[0].upper()
    # parse the url
    route = urllib.parse.unquote_plus(data[1])

    return [method, route]

def formatPath(route):
    # if the path has no file set it to index file
    if route[-1] == '/':
        route = '/index.*'
    
    # set to relative file path
    route = f"{FILE_DIR}{route}"

    # if this is a directory search for a index file
    if(os.path.isdir(route)):
        route = f'{route}/index.*'

    return route

def formatResponse(client_address, method = "GET", route = "/", content_type = "text/plain", status_code = 200, status_message = "OK", data = "", document = False):
    # set status
    header = f"HTTP/1.1 {status_code} {status_message}\r\n"
    # set response content type
    header += f"Content-Type: {content_type}\r\n"
    # set response content length
    header += f"Content-Length: {len(data)}\r\n\r\n"

    # encode the header content
    header = header.encode('utf-8')
    
    # if not a document encode the data
    if(not document):
        data = data.encode('utf-8')

    # print on terminal
    log(client_address=client_address, method=method, content_type='text/plain', status_code=status_code, route=route)
    
    # return the encoded headers
    return [header, data]

def getExtension(route):
    # split the path by '.'
    strings = route.split('.')

    # get the last string from the list
    return strings[-1]

def log(client_address, method, content_type, status_code, route):
    # format path
    route = route.replace('\\', '/')

    # create string with colors
    if(status_code == 404):
        method = f"\33[91m[{method}]\033[0m" + "\t"
        status_code = f"\33[101m {status_code} \033[0m" + "\t"
    else:
        method = f"\33[32m[{method}]\033[0m" + "\t"
        status_code = f"\33[104m {status_code} \033[0m" + "\t"

    client_address = f"\33[33m{client_address}\033[0m" + "\t"
    content_type = f"\33[90m{content_type}\033[0m" + "\t"
    route = f"{route}" + "\t"

    # print the content
    print("{0:<8} {1:<8} {2:<15} {3:<8} {4:<20}".format(client_address, method, content_type, status_code, route))

def on_client(client_socket, client_address):
    while True:
        [method, route] = formatRequest(client_socket)

        # if method or path is not found continue to the next
        if not method or not route:
            break
        
        # if the method is get::proceed
        if method == 'GET':
            route = formatPath(route)

            if len(glob.glob(route)) > 0:
                # set the found file path
                route = glob.glob(route)[0]
                # extract the file extension
                extension = getExtension(route)
                # get the content type and execution type
                content_type, execution_type, is_document = content_types.get(extension, ["text/plain", None, False])
                
                if execution_type:
                    # execute the file (eg: php) and get the output
                    output = subprocess.check_output([execution_type, route], shell=True, universal_newlines=True)
                elif is_document:
                    # read the file as binary
                    with open(route, 'rb') as file:
                        output = file.read()
                else:
                    # read the file as text
                    with open(route, 'r') as text:
                        output = text.read()
            
                # format the response with data
                [header, data] = formatResponse(
                    client_address=client_address,
                    method=method,
                    route=route,
                    content_type=content_type,
                    status_code=200,
                    status_message="OK",
                    data=output,
                    document=is_document
                )
            else:
                # format the response as not found 
                [header, data] = formatResponse(
                    client_address=client_address,
                    method=method,
                    route=route,
                    status_code=404,
                    status_message="Not Found",
                    data="Not Found"
                )
            
            # serve the response header
            client_socket.sendall(header)
            # serve the response data in chunks of buffer size
            for i in range(0, len(data), BUFFER_SIZE):
                # extract the required chunk size
                chunk = data[i:i + BUFFER_SIZE]
                # send chunk
                client_socket.sendall(chunk)
        
    # close client socket connection   
    client_socket.close()

def init():
    global server

    # initialize the socket instance
    # AF_INET means the address family ipv4
    # SOCK_STREAM means connection-oriented TCP protocol
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # set server buffer size
    server.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, BUFFER_SIZE)

    # bind the socket to localhost on given port
    server.bind((HOST, PORT))
    print(f"Server is listening on http://{HOST}:{PORT}")

    # listen to the port with 5 backlog connections
    # the sixth request will be rejected
    server.listen(5)

    # keep the server active
    while True:
        client_socket, client_address = server.accept()
        
        # create the thread
        thread = Thread(target=on_client, args=(client_socket, client_address))
        # daemon is true to make sure all processes stop when program exits
        thread.daemon = True
        # start the thread
        thread.start()  
            
# __name__ is used to make sure the server is executed directly
# not imported as a module
if __name__ == '__main__':
    try:
        # create folder if does not exist
        if(not os.path.exists(FILE_DIR)):
            os.mkdir(FILE_DIR)

        init()
    except Exception as e:
        # print error
        print(str(e))
    finally:
        # either way close the socket server
        server.close()


