"""SlowAPI: a small, testable Python web framework with indexed routing."""
from __future__ import annotations
import inspect
import re
from dataclasses import dataclass, field
from html import escape
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server
from request import Request
from response import Response

METHODS = {'GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'}

@dataclass
class Node:
    static: dict[str, 'Node'] = field(default_factory=dict)
    param: 'Node | None' = None
    param_name: str | None = None
    handlers: dict[str, tuple[Callable, tuple[Callable, ...]]] = field(default_factory=dict)

class Router:
    """Segment trie. Lookup is O(number of URL segments), not O(total routes)."""
    def __init__(self):
        self.root = Node()
        self.exact = {}  # Constant-time average-case lookup for fully static paths.
    def add(self, path, method, handler, middlewares=()):
        if not path.startswith('/'):
            raise ValueError('Route paths must begin with /')
        segments = [s for s in path.split('/') if s]
        node = self.root
        for segment in segments:
            if segment.startswith('{') and segment.endswith('}'):
                name = segment[1:-1]
                if not name.isidentifier():
                    raise ValueError('Invalid parameter name')
                if node.param is None:
                    node.param, node.param_name = Node(), name
                elif node.param_name != name:
                    raise ValueError('Ambiguous parameter route')
                node = node.param
            else:
                node = node.static.setdefault(segment, Node())
        if method in node.handlers:
            raise ValueError(f'Duplicate route: {method} {path}')
        node.handlers[method] = handler, tuple(middlewares)
        if not any(part.startswith('{') and part.endswith('}') for part in segments):
            self.exact[path] = node.handlers
    def resolve(self, path, method):
        exact = self.exact.get(path)
        if exact and method in exact:
            return exact[method], {}, set(exact)
        segments = [s for s in path.split('/') if s]
        # Prefer literal routes to dynamic routes; backtrack if literal branch dead-ends.
        stack = [(self.root, 0, {})]
        matched = []
        while stack:
            node, index, params = stack.pop()
            if index == len(segments):
                if node.handlers:
                    matched.append((node, params))
                continue
            segment = segments[index]
            if node.param is not None:
                stack.append((node.param, index+1, {**params, node.param_name: segment}))
            if segment in node.static:
                stack.append((node.static[segment], index+1, params))
        if not matched:
            return None, {}, set()
        for node, params in matched:
            if method in node.handlers:
                return node.handlers[method], params, set(node.handlers)
        allowed = set().union(*(set(node.handlers) for node, _ in matched))
        return None, {}, allowed

class SlowAPI:
    def __init__(self, middlewares=None):
        self.router = Router()
        self.middlewares = list(middlewares or [])
        self.error_handlers = {}
    def add_route(self, path, handler, method='GET', middlewares=None):
        method = method.upper()
        if method not in METHODS:
            raise ValueError('Unsupported method')
        self.router.add(path, method, handler, middlewares or ())
        return handler
    def route(self, path=None, methods=None, middlewares=None):
        def decorator(target):
            route_path = path or '/' + target.__name__
            if inspect.isclass(target):
                instance = target()
                for method in METHODS:
                    handler = getattr(instance, method.lower(), None)
                    if handler is not None:
                        self.add_route(route_path, handler, method, middlewares)
            else:
                for method in (methods or ['GET']):
                    self.add_route(route_path, target, method, middlewares)
            return target
        return decorator
    def get(self, path=None, middlewares=None): return self.route(path, ['GET'], middlewares)
    def post(self, path=None, middlewares=None): return self.route(path, ['POST'], middlewares)
    def delete(self, path=None, middlewares=None): return self.route(path, ['DELETE'], middlewares)
    def put(self, path=None, middlewares=None): return self.route(path, ['PUT'], middlewares)
    def on_error(self, status):
        def decorator(handler):
            self.error_handlers[status] = handler
            return handler
        return decorator
    def dispatch(self, request):
        response = Response()
        try:
            for middleware in self.middlewares:
                result = middleware(request)
                if isinstance(result, Response): return result
            entry, params, allowed = self.router.resolve(request.path_info, request.request_method)
            # HTTP HEAD uses the GET representation metadata when no explicit HEAD route exists.
            if entry is None and request.request_method == 'HEAD':
                get_entry, get_params, get_allowed = self.router.resolve(request.path_info, 'GET')
                if get_entry is not None:
                    entry, params = get_entry, get_params
                    allowed = allowed | get_allowed
            if entry is None:
                if allowed:
                    response.json({'error': 'Method Not Allowed'}, 405)
                    response.headers['Allow'] = ', '.join(sorted(allowed))
                else:
                    response.json({'error': 'Not Found'}, 404)
                return response
            handler, route_mws = entry
            for middleware in route_mws:
                result = middleware(request)
                if isinstance(result, Response): return result
            result = handler(request, response, **params)
            return result if isinstance(result, Response) else response
        except Exception:
            handler = self.error_handlers.get(500)
            if handler:
                return handler(request, Response())
            return Response().json({'error': 'Internal Server Error'}, 500)
    def __call__(self, environ, start_response):
        try:
            request = Request(environ)
            response = self.dispatch(request)
        except (ValueError, UnicodeError):
            response = Response().json({'error': 'Bad Request'}, 400)
        return response.as_wsgi(start_response)
    def run(self, host='127.0.0.1', port=8000, server='native'):
        if server == 'wsgi':
            instance = make_server(host, port, self)
        elif server == 'native':
            from http_server import HTTPServer
            instance = HTTPServer(host, port, self)
        else:
            raise ValueError('server must be native or wsgi')
        with instance:
            print(f'SlowAPI running at http://{host}:{port} ({server})')
            instance.serve_forever()


def render_template(filename, context=None, directory='templates'):
    """Escaped {{ placeholder }} insertion, NOT a full template language."""
    root = Path(directory).resolve()
    target = (root / filename).resolve()
    if not target.is_relative_to(root):
        raise ValueError('Template path escapes directory')
    content = target.read_text(encoding='utf-8')
    for key, value in (context or {}).items():
        if not re.fullmatch(r'[A-Za-z_]\w*', key):
            raise ValueError('Invalid template key')
        content = content.replace('{{ ' + key + ' }}', escape(str(value)))
        content = content.replace('{{'+key+'}}', escape(str(value)))
    return content
