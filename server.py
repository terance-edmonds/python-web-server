import socket
import sys
import glob
import subprocess
import json
import base64

# server configs
HOST='localhost'
PORT=2728
FILE_DIR='htdocs'

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

def formatResponse(content_type = "text/plain", status_code = 200, status_message = "OK", data = ""):
    # set status
    res = f"HTTP/1.1 {status_code} {status_message}\r\n"
    # set response content type
    res += f"Content-Type: {content_type}\r\n"
    # set response content length
    res += f"Content-Length: {len(data)}\r\n"
    # set response data
    res += f"\r\n{data}"
    
    # return the response string
    return res

def getExtension(path):
    # split the path by '.'
    strings = path.split('.')

    # get the last string from the list
    return strings[-1]

def init():
    global server

    # initialize the socket instance
    # AF_INET means the address family ipv4
    # SOCK_STREAM means connection-oriented TCP protocol
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

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

        # if method or path is not found continue to the next
        if not method or not path:
            continue
        
        # if the method is get::proceed
        if method == 'GET':
            path = formatPath(path)
            response = formatResponse()
            
            if len(glob.glob(path)) > 0:
                # set the found file path
                path = glob.glob(path)[0]
                # extract the file extension
                extension = getExtension(path)
                # get the content type and execution type
                content_type, execution_type = content_types.get(extension, ["text/plain", None])
                
                if execution_type:
                    # execute the file (eg: php) and get the output
                    output = subprocess.check_output([execution_type, path], shell=True, universal_newlines=True)
                elif "image" in content_type:
                    # read the file as binary
                    with open(path, 'rb') as file:
                        output = file.read()
                else:
                    # read the file as text
                    with open(path, 'r') as text:
                        output = text.read()

                # format the response with data
                response = formatResponse(
                    content_type=content_type,
                    status_code=200,
                    status_message="OK",
                    data=output
                )
            else:
                # format the response as not found 
                response = formatResponse(
                    status_code=404,
                    status_message="Not Found",
                    data="Not Found"
                )

            # serve the response
            client_socket.sendall(response.encode('utf-8'))

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


