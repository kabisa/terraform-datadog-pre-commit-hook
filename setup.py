from setuptools import setup

# Development setup `pip install -e .`

# I've tried pyproject.toml but console_scripts weren't supported yet
setup(
    packages=["tf_datadog_docs"],
    install_requires=["inflection", "python-hcl2", "pyyaml"],
    entry_points={
        "console_scripts": [
            "tf_datadog_docs=tf_datadog_docs:main",
            "tf_datadog_docs_index=tf_datadog_docs:add_to_local_index",
        ],
    },
)
