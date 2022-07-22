from setuptools import setup

# Development setup `pip install -e .`

# I've tried pyproject.toml but console_scripts weren't supported yet
setup(
    packages=["tf_datadog_docs"],
    install_requires=["inflection", "python-hcl2==3.0.5", "pyyaml", "lark==0.10.1"],
    entry_points={
        "console_scripts": [
            "tf_datadog_docs=tf_datadog_docs:main",
        ],
    },
)
