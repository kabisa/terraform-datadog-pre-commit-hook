#!/usr/bin/env python

import os
import sys
import textwrap

import inflection
from .hcl2mdt import load_hcl_file, HclLoadError, generate_table_for_tf_obj

INDEX_HEADER = """
| Check | Terraform File | Default Enabled |
| --- | --- | --- |
"""

PRECOMMIT_DOCS = """
# Getting started
[pre-commit](http://pre-commit.com/) was used to do Terraform linting and validating.

Steps:
   - Install [pre-commit](http://pre-commit.com/). E.g. `brew install pre-commit`.
   - Run `pre-commit install` in the repo.
   - That’s it! Now every time you commit a code change (`.tf` file), the hooks in the `hooks:` config `.pre-commit-config.yaml` will execute.
"""

INDEX_CHECK_PATTERN = "| [{check_name}](README.md#{check_name}) | [{file_name}]({file_name})  | {default_enabled}"


def get_dirs_in_path(pth):
    return [os.path.join(pth, o) for o in os.listdir(pth) if os.path.isdir(os.path.join(pth, o))]


def get_tf_files_in_path(pth):
    return [os.path.join(pth, o) for o in os.listdir(pth) if os.path.isfile(os.path.join(pth, o)) and o.endswith(".tf")]


def get_tf_variables_files_in_path(pth):
    return [o for o in get_tf_files_in_path(pth) if o.endswith("variables.tf")]


CAPITALIZE_KEYWORDS = {
    "dd": "Datadog",
    "cpu": "CPU"
}


def capitalize(inp: str):
    if inp and inp in CAPITALIZE_KEYWORDS:
        return CAPITALIZE_KEYWORDS[inp]
    if len(inp) == 1:
        return inp.upper()
    if len(inp) > 1:
        return inp[0].upper() + inp[1:]
    return inp


def get_relative_modules():
    return [module_dir for module_dir in get_dirs_in_path(os.path.abspath("../modules"))]


def main():
    path_var = sys.argv[1] if len(sys.argv) > 1 else "."
    module_dir = os.path.abspath(path_var)
    generate_docs_for_module_dir(module_dir=module_dir)


def generate_docs_for_module_dir(module_dir, precommit_docs_enabled=True):
    module_readme = os.path.join(module_dir, "README.md")
    with open(module_readme, "w") as fl:
        module_name = inflection.titleize(os.path.basename(module_dir))
        module_name = module_name.replace("Terraform ", "Terraform module for ")
        if precommit_docs_enabled:
            fl.write(f"{PRECOMMIT_DOCS}\n")

        fl.write(textwrap.dedent(f"""
            [//]: # (This file is generated. Do not edit)

            # {module_name}

            TOC:
            <!--ts-->
            <!--te-->

            """))

        module_variables = None
        for terraform_file in get_tf_variables_files_in_path(module_dir):
            try:
                obj = load_hcl_file(terraform_file)
            except HclLoadError as err:
                if "Empty Variables File" in str(err):
                    continue
                else:
                    raise
            words = list(map(capitalize, os.path.basename(terraform_file)[:-3].split("-")))
            check_name = " ".join(words[:-1])
            if check_name:
                fl.write(f"## {check_name}\n\n")
                generate_table_for_tf_obj(obj, default_value="", output_buff=fl)
                fl.write("\n\n")
            else:
                module_variables = obj

        if module_variables:
            fl.write(f"## Module Variables\n\n")
            generate_table_for_tf_obj(module_variables, default_value="", output_buff=fl)
            fl.write("\n\n")
    os.system(f"gh-md-toc --no-backup --insert {module_readme}")


if __name__ == '__main__':
    main()
