#!/usr/bin/env python
import io
import os
import sys
import textwrap

import inflection
from .hcl2mdt import load_hcl_file, HclLoadError, generate_table_for_tf_obj

INDEX_HEADER = """
| Check | Terraform File | Default Enabled |
| --- | --- | --- |
"""

PRE_COMMIT_DOCS = """
# Getting started
[pre-commit](http://pre-commit.com/) was used to do Terraform linting and validating.

Steps:
   - Install [pre-commit](http://pre-commit.com/). E.g. `brew install pre-commit`.
   - Run `pre-commit install` in the repo.
   - That’s it! Now every time you commit a code change (`.tf` file), the hooks in the `hooks:` config `.pre-commit-config.yaml` will execute.

"""

INDEX_CHECK_PATTERN = "| [{check_name}](README.md#{check_name}) | [{file_name}]({file_name})  | {default_enabled}"


def get_dirs_in_path(pth):
    return [
        os.path.join(pth, o)
        for o in os.listdir(pth)
        if os.path.isdir(os.path.join(pth, o))
    ]


def get_tf_files_in_path(pth):
    return [
        os.path.join(pth, o)
        for o in os.listdir(pth)
        if os.path.isfile(os.path.join(pth, o)) and o.endswith(".tf")
    ]


def get_tf_variables_files_in_path(pth):
    return [o for o in get_tf_files_in_path(pth) if o.endswith("variables.tf")]


CAPITALIZE_KEYWORDS = {"dd": "Datadog", "cpu": "CPU"}


def capitalize(inp: str):
    if inp and inp in CAPITALIZE_KEYWORDS:
        return CAPITALIZE_KEYWORDS[inp]
    if len(inp) == 1:
        return inp.upper()
    if len(inp) > 1:
        return inp[0].upper() + inp[1:]
    return inp


def get_relative_modules():
    return [
        module_dir for module_dir in get_dirs_in_path(os.path.abspath("../modules"))
    ]


def main():
    path_var = sys.argv[1] if len(sys.argv) > 1 else "."
    module_dir = os.path.abspath(path_var)
    generate_docs_for_module_dir(module_dir=module_dir)


def get_toc_line(line):
    count = 0
    while line.startswith("#"):
        line = line[1:]
        count += 1
    return count - 1, line.strip()


def read_intro(fl, module_dir, toc):
    intro_fl_path = os.path.join(module_dir, "intro.md")
    if os.path.isfile(intro_fl_path):
        with open(intro_fl_path, "r") as intro_fl:
            for line in intro_fl.readlines():
                if line.startswith("#"):
                    toc_level, toc_line = get_toc_line(line)
                    toc.append(toc_level * " " + f"[{toc_line}](#{canonicalize_link(toc_line)})")
                fl.write(line)


def canonicalize_link(inp: str) -> str:
    return inflection.parameterize(inp.lower(), separator="-")


def generate_docs_for_module_dir(module_dir):
    module_readme = os.path.join(module_dir, "README.md")
    toc = []
    with open(module_readme, "w") as fl:
        read_intro(fl, module_dir, toc)
        module_name = inflection.titleize(os.path.basename(module_dir))
        module_name = module_name.replace("Terraform ", "Terraform module for ")
        fl.write(
            textwrap.dedent(
                f"""![Kabisa](https://avatars.githubusercontent.com/u/1531725)
            [//]: # (This file is generated. Do not edit)

            # {module_name}

            Monitors:
            * [{module_name}](#{canonicalize_link(module_name)})
            """
            )
        )

        module_variables = None
        buff = io.StringIO()
        for terraform_file in get_tf_variables_files_in_path(module_dir):
            try:
                obj = load_hcl_file(terraform_file)
            except HclLoadError as err:
                if "Empty Variables File" in str(err):
                    continue
                else:
                    raise
            words = list(
                map(capitalize, os.path.basename(terraform_file)[:-3].split("-"))
            )
            check_name = " ".join(words[:-1])
            if check_name:
                buff.write(f"## {check_name}\n\n")
                toc.append(f"  * [{check_name}](#{canonicalize_link(check_name)})")
                generate_table_for_tf_obj(obj, default_value="", output_buff=buff)
                buff.write("\n\n")
            else:
                module_variables = obj

        if module_variables:
            buff.write(f"## Module Variables\n\n")
            toc.append(f"  * [Module Variables](#module-variables)")
            generate_table_for_tf_obj(
                module_variables, default_value="", output_buff=buff
            )
            buff.write("\n\n")

        fl.write("\n".join(toc) + "\n")

        fl.write(PRE_COMMIT_DOCS)
        buff.seek(0)
        fl.write(buff.read())


if __name__ == "__main__":
    main()
