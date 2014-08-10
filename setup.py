# -*- coding: utf-8 -*-
from setuptools import setup, find_packages
import os.path


def path(*path):
    return os.path.join(os.path.dirname(__file__), *path)


def readme():
    with open(path('README.rst')) as f:
        return f.read()


setup(name='bank',
      version='0.0.1',
      description='A command line banking utility',
      long_description=readme(),
      url='',
      author='Benoît Zugmeyer',
      author_email='benoit@zugmeyer.com',
      license='GPLv3',
      packages=find_packages(),
      install_requires=[
          'python-dateutil >=2.2,<3',
          'click >=2.4,<3',
          'requests >=2.3,<3',
          'pyyaml >=3.11,<4',
          'pyPEG2 >=2.15.0,<3',
      ],
      entry_points={
          'console_scripts': ['bank=bank.__main__:main'],
      },
      zip_safe=False,
      )
