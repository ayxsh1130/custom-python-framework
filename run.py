from wsgiref.simple_server import make_server
from example import slowapi

with make_server("", 8000, slowapi) as httpd:
    print("Serving on http://localhost:8000")
    httpd.serve_forever()