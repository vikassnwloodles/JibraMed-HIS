# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.

import os

base_url = os.environ.get('DOC_BASE_URL')
if base_url:
    modules_url = base_url + '/modules-{module}/'
    tryton_url = base_url + '/client-desktop/'
    proteus_url = base_url + '/client-library/'
else:
    modules_url = 'https://docs.tryton.org/${series}/modules-{module}/'
    tryton_url = 'https://docs.tryton.org/${series}/client-desktop/'
    proteus_url = 'https://docs.tryton.org/${series}/client-library/'


def get_info():
    import subprocess
    import sys

    module_dir = os.path.dirname(os.path.dirname(__file__))

    info = dict()

    result = subprocess.run(
        [sys.executable, 'setup.py', '--name'],
        stdout=subprocess.PIPE, check=True, cwd=module_dir)
    info['name'] = result.stdout.decode('utf-8').strip()

    result = subprocess.run(
        [sys.executable, 'setup.py', '--version'],
        stdout=subprocess.PIPE, check=True, cwd=module_dir)
    version = result.stdout.decode('utf-8').strip()
    if 'dev' in version:
        info['series'] = 'latest'
    else:
        info['series'] = '.'.join(version.split('.', 2)[:2])

    return info


info = get_info()

master_doc = 'index'
project = info['name']
release = version = info['series']
default_role = 'ref'
highlight_language = 'none'
extensions = [
    'sphinx.ext.intersphinx',
    ]
intersphinx_mapping = {
    'python': ('https://docs.python.org/', None),
    }
linkcheck_ignore = [r'/.*', r'https://demo.tryton.org/*']

del get_info, info, base_url, modules_url, tryton_url, proteus_url
