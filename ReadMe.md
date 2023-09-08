# Simple Python Web Server (Socket Programming)

This is a simple web server developed with python sockets. Server is compatible of serving various file types and also supports serving multiple clients at once.

The server also support simple GET and POST submissions.

## Example links

| Type      | Route                                                               |
| --------- | ------------------------------------------------------------------- |
| **.html** | [/](http://localhost:2728/)                                         |
| **.php**  | [/contact.php](http://localhost:2728/contact.php)                   |
| **.css**  | [/style.css](http://localhost:2728/sample/style.css)                |
| **.js**   | [/script.js](http://localhost:2728/sample/script.js)                |
| **.jpg**  | [/images/parallax1.jpg](http://localhost:2728/images/parallax1.jpg) |
| **.json** | [/files/sample.json](http://localhost:2728/files/sample.json)       |
| **.xml**  | [/files/sample.xml](http://localhost:2728/files/sample.xml)         |
| **.txt**  | [/files/sample.txt](http://localhost:2728/files/sample.txt)         |
| **.pdf**  | [/files/sample.pdf](http://localhost:2728/files/sample.pdf)         |
| **.xlsx** | [/files/sample.xlsx](http://localhost:2728/files/sample.xlsx)       |

## Requirements

- PHP 8.2.4 or up ( `php -v` for version )
- Python3 ( `python -v` for version )
- NodeJs (`node -v` for version ) [ optional ]

## Usage

Create a folder named as `htdocs` in the root directory, and add the web files to it.

Than, to start the server, Run the below code.

```bash
python serve.py
```

**For Development**

If you have `NodeJs` installed, use npm and nodemon to start the server.

```bash
npm install # install node modules
```

To run the server

```bash
npm start # run the server
```
```bash
npm run dev # run the server in development mode
```

Now open the browser and head over to [localhost:2728](http://localhost:2728).