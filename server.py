import socket
import sys
import glob
import subprocess
import json
import time

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

    return [data[0], data[1]]

def formatPath(path):
    # if the path has no file set it to index file
    if path == '/':
        path = '/index.*'
    
    # set to relative file path
    path = f"{FILE_DIR}{path}"

    return path

def formatResponse(method = "GET", path = "/", content_type = "text/plain", status_code = 200, status_message = "OK", data = "", document = False):
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
    log(method=method, content_type='text/plain', status_code=status_code, path=path)
    
    # return the encoded headers
    return [header, data]

def getExtension(path):
    # split the path by '.'
    strings = path.split('.')

    # get the last string from the list
    return strings[-1]

def log(method, content_type, status_code, path):
    # format path
    path = path.replace('\\', '/')

    # create string with colors
    if(status_code == 404):
        method = f"\33[91m[{method}]\033[0m" + "\t"
        status_code = f"\33[101m {status_code} \033[0m" + "\t"
    else:
        method = f"\33[32m[{method}]\033[0m" + "\t"
        status_code = f"\33[104m {status_code} \033[0m" + "\t"

    content_type = f"\33[90m{content_type}\033[0m" + "\t"
    path = f"{path}" + "\t"

    # print the content
    print("{0:<8} {1:<8} {2:<8} {3:<20}".format(method, content_type, status_code, path))

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
        [method, path] = formatRequest(client_socket)

        client_socket.settimeout(30)

        # if method or path is not found continue to the next
        if not method or not path:
            continue
        
        # if the method is get::proceed
        if method == 'GET':
            path = formatPath(path)
            
            if len(glob.glob(path)) > 0:
                # set the found file path
                path = glob.glob(path)[0]
                # extract the file extension
                extension = getExtension(path)
                # get the content type and execution type
                content_type, execution_type = content_types.get(extension, ["text/plain", None])
                # set is document to False
                is_document = False
                
                if execution_type:
                    # execute the file (eg: php) and get the output
                    output = subprocess.check_output([execution_type, path], shell=True, universal_newlines=True)
                elif "image" in content_type:
                    # read the file as binary
                    with open(path, 'rb') as file:
                        output = file.read()
                    # set is document True to format the response
                    is_document = True
                else:
                    # read the file as text
                    with open(path, 'r') as text:
                        output = text.read()
            
                # format the response with data
                [header, data] = formatResponse(
                    method=method,
                    path=path,
                    content_type=content_type,
                    status_code=200,
                    status_message="OK",
                    data=output,
                    document=is_document
                )
            else:
                # format the response as not found 
                [header, data] = formatResponse(
                    method=method,
                    path=path,
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
        
        time.sleep(0.1)
        # close client socket connection   
        client_socket.close()
            
# __name__ is used to make sure the server is executed directly
# not imported as a module
if __name__ == '__main__':
    try:
        init()
    except KeyboardInterrupt:
        # handle Ctrl+C (KeyboardInterrupt)
        sys.exit(0)
    finally:
        # either way close the socket server
        server.close()


