# Original Source: https://github.com/hassenius/hcl2mdtable
import re
import sys
from os.path import isfile
from typing import Dict

import hcl2


class HclLoadError(Exception):
    pass


def hcl2_list_to_dict_obj(obj: Dict) -> Dict:
    """Compatibility layer to keep support for pyhcl if we need it but try to move on to python-hcl2"""
    output = {}
    for _type, vals in obj.items():
        assert isinstance(vals, list), "isinstance(vals, list)"
        output[_type] = val_dict = {}
        for item in vals:
            for key, val in item.items():
                assert key not in val_dict, "assert key not in val_dict"
                val_dict[key] = item[key]
    return output


def load_hcl_str(hcl_str: str, hcl_file_path: str) -> Dict:
    try:
        obj = hcl2_list_to_dict_obj(hcl2.loads(hcl_str))
    except Exception as err:
        raise HclLoadError(f"{err}\nError Loading File: {hcl_file_path}")
    if str(obj) == "{}":
        raise HclLoadError(f"Empty Variables File: {hcl_file_path}")
    return obj


def load_hcl_file(hcl_file_path: str):
    with open(hcl_file_path, "r") as fp:
        contents = fp.read()
        return load_hcl_str(contents, hcl_file_path)


def generate_table_for_file(hcl_file_path: str, default_value: str, output_buff):
    obj = load_hcl_file(hcl_file_path)
    return generate_table_for_tf_obj(obj, default_value, output_buff)


def get_module_docs(obj) -> str:
    return get_module_property(obj, "docs")


def get_module_priority(obj) -> str:
    return get_module_property(obj, "priority")


def get_module_enabled(obj) -> str:
    prop_value = ""
    for key in obj["variable"].keys():
        if key.endswith(f"_enabled") and not key.endswith("_alerting_enabled"):
            prop_value = obj["variable"][key].get("default", "") or prop_value
    return bool(prop_value)


def get_module_property(obj, property_name) -> str:
    prop_value = ""
    for key in obj["variable"].keys():
        if key.endswith(f"_{property_name}"):
            prop_value = obj["variable"][key].get("default", "") or prop_value
    return prop_value


def extract_module_query(obj) -> str:
    query = ""
    if "module" not in obj:
        return query
    for module in obj["module"].values():
        query = module.get("query", "") or query
    return query


def generate_table_for_tf_obj(obj, default_value: str, output_buff):
    # Default Column Widths
    col1 = 8  # variable
    col2 = 8  # default
    col3 = 8  # required
    col4 = 12  # description

    # Calculate Column Widths
    for key in obj["variable"].keys():
        default = len(str(obj["variable"][key].get("default", "")))
        description = len(str(obj["variable"][key].get("description", "")))
        if len(str(key)) > col1:
            col1 = len(str(key))
        if default > col2:
            col2 = min(default, 40)
        if description > col4:
            col4 = min(description, 100)

    # Generate Table
    print(
        "| {} | {} | {} | {} |".format(
            "variable".ljust(col1),
            "default".ljust(col2),
            "required".ljust(col3),
            "description".ljust(col4),
        ),
        file=output_buff,
    )
    print(
        "|-{}-|-{}-|-{}-|-{}-|".format("-" * col1, "-" * col2, "-" * col3, "-" * col4),
        file=output_buff,
    )
    # print "| Variable | Default | Required | Description |"
    # print "|----------|---------|----------|-------------|"
    for key in obj["variable"].keys():
        default = obj["variable"][key].get("default", key + "%defvalue%")
        description = obj["variable"][key].get("description", "")
        if "default" in obj["variable"][key]:
            required = "No"
        else:
            required = "Yes"

        # Indicate that a blank value is an empty String
        if str(default).strip(" ") == "":
            default = '""'
        elif default == key + "%defvalue%":
            default = default_value

        print(
            "| {} | {} | {} | {} |".format(
                str(key).strip(" ").ljust(col1),
                str(default).strip(" ").ljust(col2),
                str(required).strip(" ").ljust(col3),
                str(description).strip(" ").ljust(col4),
            ),
            file=output_buff,
        )


def main():
    if len(sys.argv) < 2:
        print("Expected file name as parameter")
    file_path = sys.argv[1]
    # Default value for Variables with no Values
    default_value = ""
    if len(sys.argv) > 2:
        default_value = sys.argv[2]

    if not isfile(file_path):
        print(f"File {file_path} did not exist")
    try:
        generate_table_for_file(
            hcl_file_path=file_path, default_value=default_value, output_buff=sys.stdout
        )
    except HclLoadError as hclerr:
        print(f"{hclerr}", file=sys.stderr)


if __name__ == "__main__":
    main()
