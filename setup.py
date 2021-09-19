from setuptools import setup

# I've tried pyproject.toml but console_scripts weren't supported yet
setup(
    packages=["tf_datadog_docs"],
    install_requires=["inflection", "pyhcl"],
    entry_points={
        "console_scripts": ["tf_datadog_docs=tf_datadog_docs:main"],
    },
    scripts=["gh-md-toc"],
)
