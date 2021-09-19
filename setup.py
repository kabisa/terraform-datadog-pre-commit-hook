from setuptools import setup

setup(
    install_requires=['inflection', 'pyhcl'],
    entry_points = {
        'console_scripts': ['tf_datadog_docs=tf_datadog_docs:main'],
    }
)