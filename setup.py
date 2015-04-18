import os
import sys
from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'README.rst')) as f:
    README = f.read()

with open(os.path.join(here, 'CHANGES.rst')) as f:
    CHANGES = f.read()

with open(os.path.join(here, 'bottle_inject.py')) as f:
    for line in f:
        if line.startswith("__version__"):
            VERSION = line.strip().split('"')[-2]
            break
    else:
        raise RuntimeError("Could not find version string in module file.")

extra = {
    'install_requires': [
        'distribute',
        'bottle>=0.11',
    ]
}

if sys.version_info >= (3,):
    extra['use_2to3'] = True

setup(
    name='Bottle-Inject',
    version=VERSION,
    url='http://github.com/bottlepy/bottle-inject/',
    description='Dependency injection for Bottle.',
    long_description=README.strip() + '\n'*4 + CHANGES.strip(),
    author='Marcel Hellkamp',
    author_email='marc@gsites.de',
    license='MIT',
    platforms='any',
    zip_safe=True,
    py_modules=[
        'bottle_inject'
    ],
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    **extra
)
