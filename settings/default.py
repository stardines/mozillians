# -*- coding: utf-8 -*-

# Django settings for the mozillians project.
import logging
import os.path
import sys

from funfactory.manage import path
from funfactory import settings_base as base
from settings import MEDIA_URL, MEDIA_ROOT
from urlparse import urljoin

from apps.users.helpers import calculate_username
from django.utils.functional import lazy

## Log settings
SYSLOG_TAG = "http_app_mozillians"
LOGGING = {
    'loggers': {
        'landing': {'level': logging.INFO},
        'phonebook': {'level': logging.INFO},
    },
}

## L10n
LOCALE_PATHS = [path('locale')]

# Accepted locales
PROD_LANGUAGES = ('ca', 'cs', 'de', 'en-US', 'es', 'hu', 'fr', 'ko', 'nl',
                  'pl', 'pt-BR', 'ru', 'sk', 'sl', 'sq', 'zh-TW', 'zh-CN',
                  'lt', 'ja')

# List of RTL locales known to this project. Subset of LANGUAGES.
RTL_LANGUAGES = ()  # ('ar', 'fa', 'fa-IR', 'he')

# For absoluate urls
PROTOCOL = "https://"
PORT = 443

## Media and templates.

STATIC_ROOT = path('media/static')
STATIC_URL = MEDIA_URL + 'static/'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'jingo.Loader',
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

TEMPLATE_CONTEXT_PROCESSORS = (base.TEMPLATE_CONTEXT_PROCESSORS + (
    'django_browserid.context_processors.browserid_form',
    'apps.common.context_processors.current_year'
))

JINGO_EXCLUDE_APPS = [
    'bootstrapform',
    'admin',
    'autocomplete_light'
]

MINIFY_BUNDLES = {
    'css': {
        'common': (
            'css/main.less',
        ),
        'api': (
            'css/prettify.css',
        ),
        'test': (
            'css/qunit.css',
        ),
        'edit_profile': (
            'css/user.css',
        ),
        'register': (
            'css/register.css',
        ),
    },
    'js': {
        'common': (
            'js/libs/jquery-1.8.3.min.js',
            'js/libs/jquery-ui-1.8.7.custom.min.js',
            'js/main.js',
            'js/libs/validation/validation.js',
            'static/browserid/browserid.js',
        ),
        'homepage': (
            'js/libs/modernizr.custom.26887.js',
            'js/libs/jquery.transit.min.js',
            'js/libs/jquery.gridrotator.js',
            'js/libs/jquery.smooth-scroll.min.js',
            'js/homepage.js'
        ),
        'api': (
            'js/libs/prettify.js',
            'js/api.js',
        ),
        'edit_profile': (
            'js/libs/tag-it/js/tag-it.js',
            'js/profile_edit.js'
        ),
        'register': (
            'js/libs/tag-it/js/tag-it.js',
            'js/register.js',
        ),
        'search': (
            'js/libs/jquery.endless-scroll.js',
            'js/infinite.js',
            'js/expand.js',
        ),
        'backbone': (
            'js/libs/underscore.js',
            'js/libs/backbone.js',
            'js/libs/backbone.localStorage.js',
            'js/profiles.js',
        ),
        'test': (
            'js/libs/qunit.js',
            'js/tests/test.js',
        ),
        'profile_view': (
            'js/profile_view.js',
        ),
    }
}

LESS_PREPROCESS = False
LESS_BIN = 'lessc'

MIDDLEWARE_CLASSES = list(base.MIDDLEWARE_CLASSES) + [
    'commonware.response.middleware.StrictTransportMiddleware',
    'csp.middleware.CSPMiddleware',

    'django_statsd.middleware.GraphiteMiddleware',
    'django_statsd.middleware.GraphiteRequestTimingMiddleware',
    'django_statsd.middleware.TastyPieRequestTimingMiddleware',

    'common.middleware.StrongholdMiddleware',
    'common.middleware.UsernameRedirectionMiddleware',
    'common.middleware.OldGroupRedirectionMiddleware',
    'common.middleware.GroupAliasRedirectionMiddleware']

# StrictTransport
STS_SUBDOMAINS = True

# Not all URLs need locale.
SUPPORTED_NONLOCALES = list(base.SUPPORTED_NONLOCALES) + [
    'csp',
    'api',
    'browserid',
    'admin',
    'autocomplete',
]

AUTHENTICATION_BACKENDS = ('common.backends.MozilliansBrowserID',)

# BrowserID creates a user if one doesn't exist.
BROWSERID_CREATE_USER = True
BROWSERID_USERNAME_ALGO = calculate_username

# On Login, we redirect through register.
LOGIN_REDIRECT_URL = '/register'

INSTALLED_APPS = list(base.INSTALLED_APPS) + [
    # These need to go in order of migration.
    'users',
    'phonebook',
    'groups',
    'common',
    'api',
    'mozspaces',
    'funfacts',
    'announcements',

    'csp',
    'jingo_minify',
    'tower',
    'cronjobs',
    'elasticutils',
    'sorl.thumbnail',
    'autocomplete_light',

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.staticfiles',
    'django_browserid',
    'bootstrapform',

    # DB migrations
    'south',
    # re-assert dominance of 'django_nose'
    'django_nose',
]

## Auth
PWD_ALGORITHM = 'bcrypt'
HMAC_KEYS = {
    '2011-01-01': 'cheesecake',
}

SESSION_COOKIE_HTTPONLY = True
SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
ANON_ALWAYS = True

# Email
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Auth
LOGIN_URL = '/'
LOGIN_REDIRECT_URL = '/'

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
    }
}

AUTH_PROFILE_MODULE = 'users.UserProfile'

MAX_PHOTO_UPLOAD_SIZE = 8 * (1024 ** 2)

AUTO_VOUCH_DOMAINS = ('mozilla.com', 'mozilla.org', 'mozillafoundation.org')
SOUTH_TESTS_MIGRATE = False

# Django-CSP
CSP_FONT_SRC = ("'self'",
                'https://www.mozilla.org',
                'https://mozorg.cdn.mozilla.net')
CSP_FRAME_SRC = ("'self'", 'https://browserid.org',
                 'https://login.persona.org',)
CSP_IMG_SRC = ("'self'",
               "'self' data:",
               'https://mozorg.cdn.mozilla.net',
               'http://www.google-analytics.com',
               'https://ssl.google-analytics.com',
               'http://www.gravatar.com',
               'https://i1.wp.com',
               'https://secure.gravatar.com',)
CSP_SCRIPT_SRC = ("'self'",
                  'https://www.mozilla.org',
                  'https://mozorg.cdn.mozilla.net',
                  'http://www.google-analytics.com',
                  'https://ssl.google-analytics.com',
                  'https://www.google-analytics.com',
                  'https://browserid.org',
                  'https://login.persona.org',)
CSP_STYLE_SRC = ("'self'",
                 'https://www.mozilla.org',
                 'https://mozorg.cdn.mozilla.net',)
CSP_REPORT_ONLY = True
CSP_REPORT_URI = '/csp/report/'

ES_DISABLED = True
ES_HOSTS = ['127.0.0.1:9200']
ES_INDEXES = {'default': 'mozillians',
              'public': 'mozillians-public'}
ES_INDEXING_TIMEOUT = 10

# Sorl settings
THUMBNAIL_DUMMY = True
THUMBNAIL_PREFIX = 'uploads/sorl-cache/'

# Statsd Graphite
STATSD_CLIENT = 'django_statsd.clients.normal'

# Basket
# If we're running tests, don't hit the real basket server.
if 'test' in sys.argv:
    BASKET_URL = 'http://127.0.0.1'
else:
    BASKET_URL = 'http://basket.mozilla.com'
BASKET_NEWSLETTER = 'mozilla-phone'

USER_AVATAR_DIR = 'uploads/userprofile'
MOZSPACE_PHOTO_DIR = 'uploads/mozspaces'
ANNOUNCEMENTS_PHOTO_DIR = 'uploads/announcements'

# Google Analytics
GA_ACCOUNT_CODE = 'UA-35433268-19'

# Set ALLOWED_HOSTS based on SITE_URL.
def _allowed_hosts():
    from django.conf import settings
    from urlparse import urlparse

    host = urlparse(settings.SITE_URL).netloc # Remove protocol and path
    host = host.rsplit(':', 1)[0]  # Remove port
    return [host]
ALLOWED_HOSTS = lazy(_allowed_hosts, list)()

STRONGHOLD_EXCEPTIONS = ['^%s' % MEDIA_URL,
                         '^/csp/',
                         '^/admin/',
                         '^/browserid/verify/',
                         '^/api']

# Set default avatar for user profiles
DEFAULT_AVATAR= 'img/unknown.png'
DEFAULT_AVATAR_URL = urljoin(MEDIA_URL, DEFAULT_AVATAR)
DEFAULT_AVATAR_PATH = os.path.join(MEDIA_ROOT, DEFAULT_AVATAR)

CELERYBEAT_SCHEDULER = "djcelery.schedulers.DatabaseScheduler"
