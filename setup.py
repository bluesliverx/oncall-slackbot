import os
import subprocess
from setuptools import setup, find_packages


MAJOR_VERSION = '1'

version_file = os.path.join(os.path.dirname(__file__), 'oncall_slackbot/VERSION')
if os.path.exists(version_file):
    # Read version from file
    with open(version_file, 'r', encoding='utf8') as fobj:
        version = fobj.read().strip()
else:
    # Generate the version and store it in the file
    result = subprocess.run('git rev-list --count HEAD', shell=True, capture_output=True, encoding='utf8')
    commit_count = result.stdout.strip()
    version = f'{MAJOR_VERSION}.{commit_count}'
    print(f'Setting version to {version} and writing to {version_file}')
    with open(version_file, 'w', encoding='utf8') as fobj:
        fobj.write(version)

install_requires = (
    'slackbot==0.5.5',
    'pygerduty>=0.38.2',
    'pytz>=2019.3',
    'humanize>=0.5.1',
    'spacy==2.2.3',
)  # yapf: disable

excludes = (
    '*test*',
    '*local_settings*',
) # yapf: disable

setup(name='oncall-slackbot',
      version=version,
      license='MIT',
      description='Extended slackbot made specifically to handle on-call requests',
      author='Brian Saville',
      author_email='bksaville@gmail.com',
      url='http://github.com/bluesliverx/oncall-slackbot',
      platforms=['Any'],
      packages=find_packages(exclude=excludes),
      install_requires=install_requires,
      classifiers=['Development Status :: 4 - Beta',
                   'License :: OSI Approved :: MIT License',
                   'Operating System :: OS Independent',
                   'Programming Language :: Python',
                   'Programming Language :: Python :: 2',
                   'Programming Language :: Python :: 2.7',
                   'Programming Language :: Python :: 3',
                   'Programming Language :: Python :: 3.4',
                   'Programming Language :: Python :: 3.5',
                   'Programming Language :: Python :: 3.6'])
