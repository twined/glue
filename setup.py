# -*- coding: utf-8 -*-
from distutils.core import setup
from setuptools import find_packages

setup(
    name='glue',
    version='0.1.5',
    author=u'Twined',
    author_email='www.twined.net',
    packages=find_packages(),
    include_package_data=True,
    url='http://github.com/twined/glue',
    license='Do what thou wilt.',
    description='fabfile stuff for django',
    long_description=open('README.md').read(),
    zip_safe=False,
)
