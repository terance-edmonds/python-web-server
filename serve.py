import socket
import glob
import subprocess
import json
import urllib.parse
import os
from threading import Thread
import re

# server configs
HOST = 'localhost'
PORT = 2728
FILE_DIR = 'htdocs'
BUFFER_SIZE = 8192  # 8KB

# socket server
server = None

# content types for different file extensions
# along with an execute type
content_types_file = open('content-types.json')
content_types = json.load(content_types_file)


def getBody(request):
    data = {}
    # regex patterns to get the data for relevant pattern
    patterns = {
        "multipart/form-data": r'Content-Disposition: form-data; name="([^"]+)"\s+([\s\S]+?)(?=\n-{2,})',
        "application/x-www-form-urlencoded": r"([^&]+)=([^&]+)",
        "text/plain": r"([^=\r\n]+)=([^=\r\n]+)"
    }

    chunks = request.split("\r\n\r\n", 1)
    header = ""
    body = ""
    # separate the body and header
    for chunk in chunks:
        if "HTTP/1.1" in chunk:
            header = chunk
            continue

        body += chunk + "\r\n\r\n"

    # extract the content type
    ct_match = re.search(r'Content-Type:\s*([^;\r\n]+)', header)
    if not ct_match:
        return data

    # see if the content type has a pattern
    content_type = ct_match.group(1)
    if content_type not in patterns:
        return data

    # extract matching strings
    matches = re.findall(patterns[content_type], body)

    # iterate through the matches and store them in the dictionary
    for match in matches:
        name = match[0].strip()
        value = match[1].strip()

        # make the strings to readable format
        name = urllib.parse.unquote_plus(name)
        value = urllib.parse.unquote_plus(value)

        # add to dictionary
        data[name] = value

    return data


def getParams(route):
    parsed_url = urllib.parse.urlparse(route)
    query_params = urllib.parse.parse_qs(parsed_url.query)
    data = {}
    # iterate through and store them in the dictionary
    for key, values in query_params.items():
        if (len(values) == 1):
            values = values[0]
        data[key] = values

    return data


def loadRequest(client_socket):
    # get data from http client request (max 1KB) as chunks
    # format into a string
    request = ""
    content_length = 0
    received_length = 0
    while True:
        chunk = client_socket.recv(1024).decode('utf-8')

        # get the content length if available
        cl_match = re.search(r'Content-Length:\s*(\d+)', chunk)
        if (cl_match):
            content_length = int(cl_match.group(1))

        # split the chunk
        chunk_split = chunk.split("\r\n\r\n", 1)

        # add the length of body content
        for ch in chunk_split:
            if ("HTTP/1.1" in ch):
                continue

            received_length += len(ch)

        if not chunk:
            break  # no more data is being sent by the client

        # add to request data
        request += chunk

        # if content length is satisfied exit the request data collection
        if (received_length >= content_length):
            break

    return request


def formatRequest(request):
    if not request:
        return [None, None, None, None]

    # split the request string into lines
    lines = request.split('\r\n')
    # get the first line and split by space
    data = lines[0].split()
    method = data[0].upper()
    # parse the url
    route = urllib.parse.unquote_plus(data[1]) if (len(data) > 1) else None
    # get body data if available
    body = getBody(request)
    # get parameter data if available
    params = getParams(route)

    return [method, route, body, params]


def formatPath(route):
    route_split = route.split("?")
    route_path = route_split[0]

    # if the path has no file set it to index file
    if route_path[-1] == '/':
        route_path = '/index.*'

    # set to relative file path
    route_path = f"{FILE_DIR}{route_path}"

    # if this is a directory search for a index file
    if (os.path.isdir(route_path)):
        route_path = f'{route_path}/index.*'

    return route_path


def formatResponse(client_address, method="GET", route="/", content_type="text/plain", status_code=200, status_message="OK", data="", document=False):
    # set status
    header = f"HTTP/1.1 {status_code} {status_message}\r\n"
    # set response content type
    header += f"Content-Type: {content_type}\r\n"
    # set response content length
    header += f"Content-Length: {len(data)}\r\n"
    # set the empty line
    header += "\r\n"

    # encode the header content
    header = header.encode('utf-8')

    # if not a document encode the data
    if (not document):
        data = data.encode('utf-8')

    # print on terminal
    log(client_address=client_address, method=method,
        content_type=content_type, status_code=status_code, route=route)

    # return the encoded headers
    return [header, data]


def getExtension(route):
    # split the path by '.'
    strings = route.split('.')

    # get the last string from the list
    return strings[-1]


def formatDictToString(body, params):
    string = ""
    for key, value in params.items():
        quote = "\""

        # to make sure the string doesn't break
        if ("\"" in value):
            quote = "\'"
        elif ("\'" in value):
            quote = "`"

        string += f"$_GET[\"{key}\"]={quote}{value}{quote};\r\n"

    for key, value in body.items():
        quote = "\""

        # to make sure the string doesn't break
        if ("\"" in value):
            quote = "\'"
        elif ("\'" in value):
            quote = "`"

        string += f"$_POST[\"{key}\"]={quote}{value}{quote};\r\n"

    return string


def log(client_address, method, content_type, status_code, route):
    if (method not in ["GET", "POST"]):
        return

    # format path
    route = route.replace('\\', '/')

    # create string with colors
    if (status_code == 404):
        method = f"\33[91m[{method}]\033[0m" + "\t"
        status_code = f"\33[101m {status_code} \033[0m" + "\t"
    else:
        method = f"\33[32m[{method}]\033[0m" + "\t"
        status_code = f"\33[104m {status_code} \033[0m" + "\t"

    client_address = f"\33[33m{client_address}\033[0m" + "\t"
    content_type = f"\33[90m{content_type}\033[0m" + "\t"
    route = f"{route}" + "\t"

    # print the content
    print("{0:<8} {1:<8} {2:<15} {3:<8} {4:<20}".format(
        client_address, method, content_type, status_code, route))


def onClient(client_socket, client_address):
    while True:
        # connect all request chunks
        request = loadRequest(client_socket)
        [method, route, body, params] = formatRequest(request)

        # if method or path is not found continue to the next
        if not method or not route:
            break

        # if the method is get::proceed
        route = formatPath(route)

        if len(glob.glob(route)) > 0:
            # set the found file path
            route = glob.glob(route)[0]
            # extract the file extension
            extension = getExtension(route)
            # get the content type and execution type
            content_type, execution_type, is_document = content_types.get(
                extension, ["text/plain", None, False])

            if execution_type:
                with open(route, 'r+') as file:
                    # read the file content
                    content = file.read()
                    # set the pointer back to the start of the file
                    file.seek(0, 0)

                    # prepare form data
                    form_data = formatDictToString(body, params)

                    # append the form content
                    content = content.replace(
                        "<?php", f"<?php \r\n{form_data}\r\n")
                    # execute the command and pass the script content as stdin
                    process = subprocess.Popen([execution_type], stdin=subprocess.PIPE,
                                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
                    # communicate with the process, passing the PHP script content as input
                    output, error = process.communicate(input=content)

                    if (error):
                        output = error
                        content_type = "text/plain"

                        print(f"error: {error}")
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
        thread = Thread(target=onClient, args=(client_socket, client_address))
        # daemon is true to make sure all processes stop when program exits
        thread.daemon = True
        # start the thread
        thread.start()


# __name__ is used to make sure the server is executed directly
# not imported as a module
if __name__ == '__main__':
    try:
        # create folder if does not exist
        if (not os.path.exists(FILE_DIR)):
            os.mkdir(FILE_DIR)

        init()
    except Exception as e:
        # print error
        print(str(e))
    finally:
        # either way close the socket server
        server.close()
