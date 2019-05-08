#!/usr/bin/env python3

import argparse
import json
import logging
import os
import re
import sys
import time
from subprocess import PIPE, Popen

import jinja2

BREW_PATH = '/usr/local/bin/brew'
GIT_PATH = '/usr/local/bin/git'
HOMEBREW_FORMULA_DIR = '/usr/local/Homebrew/Library/Taps/homebrew/homebrew-core/Formula'
TEMPLATE_DIR = os.path.dirname(os.path.realpath(__file__))
TEMPLATE_FILE = 'page.tmpl'
TEMPLATE_OUTPUT = f'/tmp/show-urls-for-recent-homebrews-{time.strftime("%A-%-I%M%p", time.localtime())}.html'
TEMPLATE_OUTPUT_SYMLINK = '/tmp/show-urls-for-recent-homebrews.html'
TERMINAL_NOTIFIER = '/usr/local/bin/terminal-notifier'

parser = argparse.ArgumentParser()

parser.add_argument(
    "-s",
    "--since-seconds",
    type=str,
    const=1,
    default=str(24 * 60 * 60),
    nargs='?',
    help="show changes since this many seconds ago. eg for changes within the last  2 days, use -s '2*24*60*60'")

parser.add_argument(
    "-n",
    "--no-notify",
    action='store_true',
    default=False,
    help="Do not send notification to terminal.")

parser.add_argument(
    "--debug",
    action='store_true',
    default=False,
    help="debug")

args = parser.parse_args()

if args.debug:
    format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=format,
                        level=logging.DEBUG, datefmt="%H:%M:%S")

my_env = os.environ.copy()
my_env["HOME"] = ""  # hide $HOME/.gitconfig from git
my_env["PATH"] = f'/usr/local/bin:{my_env["PATH"]}'

cmd = ['git', 'log', '--format=%h',
       f'--since={eval(args.since_seconds)}.seconds.ago']
process = Popen(
    cmd,
    cwd=HOMEBREW_FORMULA_DIR,
    stdout=PIPE,
    stderr=PIPE,
    env=my_env,
    encoding='utf8')

stdout, stderr = process.communicate()
shas = stdout.split('\n')
shas.remove('')
logging.debug(f"{' '.join(cmd)} output: {' '.join(shas)}")

if not shas:
    sys.exit(0)

cmd = [
    GIT_PATH,
    'diff',
    '--name-only',
    f'{shas[-1]}..master',
]
logging.debug(f"{' '.join(cmd)}")
process = Popen(
    cmd,
    cwd=HOMEBREW_FORMULA_DIR,
    stdout=PIPE,
    stderr=PIPE,
    env=my_env,
    encoding='utf8')
stdout, stderr = process.communicate()
shas = [re.sub(r'Formula/(.*)\.rb', r'\1', x, flags=re.I)
        for x in stdout.split('\n') if x != '']

cmd = [BREW_PATH, 'info', '--json'] + shas
logging.debug(f"{' '.join(cmd)}")
process = Popen(
    cmd,
    cwd=HOMEBREW_FORMULA_DIR,
    stdout=PIPE,
    stderr=PIPE,
    encoding='utf8')
stdout, stderr = process.communicate()

dct_brews = json.loads(stdout)

templateLoader = jinja2.FileSystemLoader(searchpath=TEMPLATE_DIR)
templateEnv = jinja2.Environment(loader=templateLoader)
template = templateEnv.get_template(TEMPLATE_FILE)
output = template.render(my_list=dct_brews)

with open(TEMPLATE_OUTPUT, 'w') as html:
    html.write(output)

if not args.no_notify:
    cmd = [
        TERMINAL_NOTIFIER,
        '-title',
        'Homebrew',
        '-message',
        'Homebrew updates',
        '-open',
        f'file://{TEMPLATE_OUTPUT}',
    ]
    process = Popen(
        cmd,
        cwd=HOMEBREW_FORMULA_DIR,
        stdout=PIPE,
        stderr=PIPE,
        encoding='utf8')
    stdout, stderr = process.communicate()

tmplink = f'{TEMPLATE_OUTPUT}.tmp'
os.symlink(TEMPLATE_OUTPUT, tmplink)
os.rename(tmplink, TEMPLATE_OUTPUT_SYMLINK)
