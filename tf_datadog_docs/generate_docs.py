#!/usr/bin/env python
import io
import os
import sys
import textwrap
from os.path import expanduser, isfile, basename, isdir, join

import inflection
import yaml

from tf_datadog_docs.hcl2mdt import (
    load_hcl_file,
    HclLoadError,
    generate_table_for_tf_obj,
    get_module_docs,
    get_module_priority,
    get_module_enabled,
    extract_module_query,
    get_module_property,
)

INDEX_HEADER = """
| Check | Terraform File | Default Enabled |
| --- | --- | --- |
"""

PRE_COMMIT_DOCS = """
# Getting started developing
[pre-commit](http://pre-commit.com/) was used to do Terraform linting and validating.

Steps:
   - Install [pre-commit](http://pre-commit.com/). E.g. `brew install pre-commit`.
   - Run `pre-commit install` in this repo. (Every time you clone a repo with pre-commit enabled you will need to run the pre-commit install command)
   - That’s it! Now every time you commit a code change (`.tf` file), the hooks in the `hooks:` config `.pre-commit-config.yaml` will execute.

"""

INDEX_CHECK_PATTERN = "| [{check_name}](README.md#{check_name}) | [{file_name}]({file_name})  | {default_enabled}"


def get_dirs_in_path(pth):
    return [
        join(pth, o)
        for o in os.listdir(pth)
        if os.path.isdir(join(pth, o))
    ]


def get_tf_files_in_path(pth):
    return [
        join(pth, o)
        for o in os.listdir(pth)
        if os.path.isfile(join(pth, o)) and o.endswith(".tf")
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


def main(module_dir=None):
    if module_dir is None:
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
    intro_fl_path = join(module_dir, "intro.md")
    if os.path.isfile(intro_fl_path):
        with open(intro_fl_path, "r") as intro_fl:
            for line in intro_fl.readlines():
                if line.startswith("#"):
                    toc_level, toc_line = get_toc_line(line)
                    toc.append(
                        toc_level * " "
                        + f"[{toc_line}](#{canonicalize_link(toc_line)})"
                    )
                fl.write(line)


def canonicalize_link(inp: str) -> str:
    return inflection.parameterize(inp.lower(), separator="-")


def canonicalize_module_name(inp: str) -> str:
    return inflection.parameterize(inp.lower(), separator="_")


def loop_variable_files(module_dir: str):
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
        yield check_name, terraform_file, obj


def get_examples(module_dir: str) -> str:
    examples_dir = join(module_dir, "examples")
    if not isdir(examples_dir):
        return ""

    example_files = get_tf_files_in_path(examples_dir)
    if not example_files:
        return ""

    examples = "\n# Example Usage"
    for example_file in example_files:
        with open(example_file, "r") as fl:
            examples += "\n\n```terraform\n"
            for line in fl.readlines():
                if line.startswith("# tflint-ignore:"):
                    continue
                examples += line
            examples += "\n```\n"

    return examples


def generate_docs_for_module_dir(module_dir):
    module_readme = join(module_dir, "README.md")
    module_description_md = join(module_dir, "module_description.md")
    module_description = ""
    toc = []
    if isfile(module_description_md):
        with open(module_description_md, "r") as fl:
            module_description = fl.read()
        if not module_description.startswith("\n"):
            module_description = "\n" + module_description
        if not module_description.endswith("\n"):
            module_description = module_description + "\n"

    module_examples = get_examples(module_dir)

    with open(module_readme, "w") as fl:
        read_intro(fl, module_dir, toc)
        module_name = inflection.titleize(os.path.basename(module_dir))
        module_name = module_name.replace("Terraform ", "Terraform module for ")
        fl.write(
            f"""
![Datadog](https://imgix.datadoghq.com/img/about/presskit/logo-v/dd_vertical_purple.png)

[//]: # (This file is generated. Do not edit, module description can be added by editing / creating module_description.md)

# {module_name}
{module_description}
This module is part of a larger suite of modules that provide alerts in Datadog.
Other modules can be found on the [Terraform Registry](https://registry.terraform.io/search/modules?namespace=kabisa&provider=datadog)

We have two base modules we use to standardise development of our Monitor Modules:
- [generic monitor](https://github.com/kabisa/terraform-datadog-generic-monitor) Used in 90% of our alerts
- [service check monitor](https://github.com/kabisa/terraform-datadog-service-check-monitor)

Modules are generated with this tool: https://github.com/kabisa/datadog-terraform-generator
{module_examples}

[Module Variables](#module-variables)

Monitors:

"""
        )

        module_variables = None
        module_buff = io.StringIO()
        overview = {}
        for monitor_name, terraform_file, obj in loop_variable_files(module_dir):
            if monitor_name:
                module_buff.write(f"## {monitor_name}\n\n")
                module_docs = get_module_docs(obj)
                if module_docs:
                    module_buff.write(module_docs + "\n\n")
                default_enabled = get_module_enabled(obj)
                module_priority = get_module_priority(obj)
                module_query = get_expanded_module_query(
                    terraform_file=terraform_file,
                    vars_obj=obj,
                    check_name_underscored=canonicalize_module_name(monitor_name),
                )

                markdown_link = f"[{monitor_name}](#{canonicalize_link(monitor_name)})"

                if module_query:
                    module_buff.write(wrap_query_docs(module_query) + "\n\n")
                    overview[markdown_link] = [str(default_enabled), str(module_priority), module_query]

                generate_table_for_tf_obj(obj, default_value="", output_buff=module_buff)
                module_buff.write("\n\n")
            else:
                module_variables = obj

        if module_variables:
            module_buff.write(f"## Module Variables\n\n")
            generate_table_for_tf_obj(
                module_variables, default_value="", output_buff=module_buff
            )
            module_buff.write("\n\n")

        write_overview_table(overview, fl)

        fl.write(PRE_COMMIT_DOCS)

        module_buff.seek(0)
        fl.write(module_buff.read())


def write_overview_table(overview, fl):
    # Default Column Widths
    monitor_name = 15
    default_enabled = 4
    module_priority = 2
    module_query = 22

    print(
        "| {} | {} | {} | {} |".format(
            "Monitor name".ljust(monitor_name),
            "Default enabled".ljust(default_enabled),
            "Priority".ljust(module_priority),
            "Query".ljust(module_query),
        ),
        file=fl,
    )
    print(
        "|-{}-|-{}-|-{}-|-{}-|".format("-" * monitor_name, "-" * default_enabled, "-" * module_priority, "-" * module_query),
        file=fl,
    )

    for key in sorted(overview):
        item = overview[key]
        print(
            "| {} | {} | {} | {} |".format(
                str(key).strip(" ").ljust(monitor_name),
                str(item[0]).strip(" ").ljust(default_enabled),
                str(item[1]).strip(" ").ljust(module_priority),
                str(item[2]).strip(" ").ljust(module_query),
            ),
            file=fl,
        )


def get_module_query(terraform_file):
    module_file_path = terraform_file.replace("-variables.tf", ".tf")
    try:
        obj = load_hcl_file(module_file_path)
    except Exception as ex:
        return print(ex, file=sys.stderr)
    return extract_module_query(obj)


def expand_module_query(obj, check_name_underscored, query):
    query = query.replace(
        f"${{var.{check_name_underscored}_evaluation_period}}",
        get_module_property(obj, "evaluation_period"),
    )
    query = query.replace(
        f"${{var.{check_name_underscored}_critical}}",
        str(get_module_property(obj, "critical")),
    )
    query = query.replace(f"${{local.{check_name_underscored}_filter}}", "tag:xxx")
    return query


def get_expanded_module_query(terraform_file, vars_obj, check_name_underscored):
    query = get_module_query(terraform_file)
    if query:
        query = expand_module_query(vars_obj, check_name_underscored, query)
    return query


def wrap_query_docs(query):
    if query:
        query = textwrap.dedent(
            f"""
            Query:
            ```terraform
            {query}
            ```
            """
        ).strip()
    return query


def add_to_local_index(module_dir=None):
    if module_dir is None:
        path_var = sys.argv[1] if len(sys.argv) > 1 else "."
        module_dir = os.path.abspath(path_var)

    index_loc = expanduser("~/.datadog-terraform-monitor-index.yaml")
    if isfile(index_loc):
        with open(index_loc, "r") as fl:
            index = yaml.safe_load(fl)
    else:
        index = {}

    module_name = basename(module_dir)
    if module_name not in index:
        index[module_name] = {}
    for check_name, terraform_file, obj in loop_variable_files(module_dir):
        if check_name:
            check_name_underscored = canonicalize_module_name(check_name)
            index[module_name][check_name] = module_info = {
                "docs": get_module_docs(obj),
                "name": check_name,
                "query": get_module_query(terraform_file),
                "evaluation_period": get_module_property(obj, "evaluation_period"),
                "default_enabled": get_module_enabled(obj, "enabled"),
                "priority": get_module_property(obj, "priority"),
                "critical": get_module_property(obj, "critical"),
            }
            if module_info["query"]:
                module_info["query"] = expand_module_query(
                    obj, check_name_underscored, module_info["query"]
                )

    with open(index_loc, "w") as fl:
        yaml.safe_dump(index, fl)


if __name__ == "__main__":
    main("/Users/sjuuljanssen/workspace/terraform-datadog-kubernetes")
