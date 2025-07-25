# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import base64
import gzip
import logging
import time
from io import BytesIO
from functools import wraps
try:
    from http import HTTPStatus
except ImportError:
    from http import client as HTTPStatus

from werkzeug.wrappers import Request as _Request, Response
from werkzeug.datastructures import Authorization
from werkzeug.exceptions import abort, HTTPException

from trytond import security, backend
from trytond.exceptions import RateLimitException
from trytond.pool import Pool
from trytond.tools import cached_property
from trytond.transaction import Transaction
from trytond.config import config

logger = logging.getLogger(__name__)


class Request(_Request):

    view_args = None

    def __repr__(self):
        args = []
        try:
            if self.url is None or isinstance(self.url, str):
                url = self.url
            else:
                url = self.url.decode(getattr(self, 'url_charset', 'utf-8'))
            auth = self.authorization
            if auth:
                args.append("%s@%s" % (
                        auth.get('userid', auth.username), self.remote_addr))
            else:
                args.append(self.remote_addr)
            args.append("'%s'" % url)
            args.append("[%s]" % self.method)
            if self.view_args:
                args.append("%s" % (self.rpc_method or ''))
        except Exception:
            args.append("(invalid WSGI environ)")
        return "<%s %s>" % (
            self.__class__.__name__, " ".join(filter(None, args)))

    @property
    def decoded_data(self):
        if self.content_encoding == 'gzip':
            if self.user_id:
                zipfile = gzip.GzipFile(fileobj=BytesIO(self.data), mode='rb')
                return zipfile.read()
            else:
                abort(HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
        else:
            return self.data

    @property
    def parsed_data(self):
        return self.data

    @property
    def rpc_method(self):
        return

    @property
    def rpc_params(self):
        return

    @cached_property
    def authorization(self):
        authorization = super(Request, self).authorization
        if authorization is None:
            header = self.headers.get('Authorization')
            return parse_authorization_header(header)
        elif authorization.type == 'session':
            # Werkzeug may parse the session as parameters
            # if the base64 uses the padding sign '='
            if authorization.token is None:
                header = self.headers.get('Authorization')
                return parse_authorization_header(header)
            else:
                return parse_session(authorization.token)
        return authorization

    @cached_property
    def user_id(self):
        assert self.view_args is not None
        database_name = self.view_args.get('database_name')
        if not database_name:
            return None
        auth = self.authorization
        if not auth:
            return None
        context = {'_request': self.context}
        if auth.type == 'session':
            user_id = security.check(
                database_name, auth.get('userid'), auth.get('session'),
                context=context)
        elif auth.username:
            parameters = getattr(auth, 'parameters', auth)
            try:
                user_id = security.login(
                    database_name, auth.username, parameters, cache=False,
                    context=context)
            except RateLimitException:
                abort(HTTPStatus.TOO_MANY_REQUESTS)
        else:
            user_id = None
        return user_id

    @cached_property
    def context(self):
        return {
            'remote_addr': self.remote_addr,
            'http_host': self.environ.get('HTTP_HOST'),
            'scheme': self.scheme,
            'is_secure': self.is_secure,
            }


def parse_authorization_header(value):
    if not value:
        return
    if isinstance(value, bytes):
        value = value.decode('latin1')
    try:
        auth_type, auth_info = value.split(None, 1)
        auth_type = auth_type.lower()
    except ValueError:
        return
    if auth_type == 'session':
        return parse_session(auth_info)
    else:
        authorization = Authorization(auth_type)
        authorization.token = auth_info
        return authorization


def parse_session(token):
    try:
        username, userid, session = (
            base64.b64decode(token).decode().split(':', 3))
        userid = int(userid)
    except Exception:
        return
    return Authorization('session', {
            'username': username,
            'userid': userid,
            'session': session,
            })


def set_max_request_size(size):
    def decorator(func):
        func.max_request_size = size
        return func
    return decorator


def allow_null_origin(func):
    func.allow_null_origin = True
    return func


def with_pool(func):
    @wraps(func)
    def wrapper(request, database_name, *args, **kwargs):
        database_list = Pool.database_list()
        pool = Pool(database_name)
        if database_name not in database_list:
            with Transaction().start(database_name, 0, readonly=True):
                pool.init()
        return func(request, pool, *args, **kwargs)
    return wrapper


def with_transaction(readonly=None, user=0, context=None):
    from trytond.worker import run_task

    def decorator(func):
        @wraps(func)
        def wrapper(request, pool, *args, **kwargs):
            readonly_ = readonly  # can not modify non local
            if readonly_ is None:
                if request.method in {'POST', 'PUT', 'DELETE', 'PATCH'}:
                    readonly_ = False
                else:
                    readonly_ = True
            if context is None:
                context_ = {}
            else:
                context_ = context.copy()
            context_['_request'] = request.context
            if user == 'request':
                user_ = request.user_id
            else:
                user_ = user
            retry = config.getint('database', 'retry')
            for count in range(retry, -1, -1):
                if count != retry:
                    time.sleep(0.02 * (retry - count))
                with Transaction().start(
                        pool.database_name, user_, readonly=readonly_,
                        context=context_) as transaction:
                    try:
                        result = func(request, pool, *args, **kwargs)
                    except backend.DatabaseOperationalError:
                        if count and not readonly_:
                            transaction.rollback()
                            transaction.tasks.clear()
                            continue
                        logger.error('%s', request, exc_info=True)
                        raise
                    except Exception as e:
                        if isinstance(e, HTTPException):
                            raise
                        logger.error('%s', request, exc_info=True)
                        raise
                    # Need to commit to unlock SQLite database
                    transaction.commit()
                while transaction.tasks:
                    task_id = transaction.tasks.pop()
                    run_task(pool, task_id)
                return result
        return wrapper
    return decorator


def user_application(name, json=True):
    from .jsonrpc import JSONEncoder, json as json_

    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            pool = Pool()
            UserApplication = pool.get('res.user.application')

            authorization = request.authorization
            if authorization is None:
                header = request.headers.get('Authorization')
                authorization = parse_authorization_header(header)
            if authorization is None:
                abort(HTTPStatus.UNAUTHORIZED)
            if authorization.type != 'bearer':
                abort(HTTPStatus.FORBIDDEN)

            token = getattr(authorization, 'token', '')
            application = UserApplication.check(token, name)
            if not application:
                abort(HTTPStatus.FORBIDDEN)
            transaction = Transaction()
            # TODO language
            with transaction.set_user(application.user.id), \
                    transaction.set_context(_check_access=True):
                try:
                    response = func(request, *args, **kwargs)
                except Exception as e:
                    if isinstance(e, HTTPException):
                        raise
                    logger.error('%s', request, exc_info=True)
                    abort(HTTPStatus.INTERNAL_SERVER_ERROR, e)
            if not isinstance(response, Response) and json:
                response = Response(json_.dumps(response, cls=JSONEncoder),
                    content_type='application/json')
            return response
        return wrapper
    return decorator
