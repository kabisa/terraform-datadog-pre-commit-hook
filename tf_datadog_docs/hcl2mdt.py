# Original Source: https://github.com/hassenius/hcl2mdtable

import sys
from os.path import isfile

import hcl


class HclLoadError(Exception):
    pass


def load_hcl_file(hcl_file_path: str):
    with open(hcl_file_path, "r") as fp:
        try:
            obj = hcl.load(fp)
        except ValueError as err:
            raise HclLoadError(
                f"{err}\n{hcl_file_path}\nNote: pyhcl 0.4.4 and below do not seem to support validation sections in variables."
            )
        except Exception as err:
            raise HclLoadError(f"{err}\nError Loading File: {hcl_file_path}, May need to update pyhcl.")
        if str(obj) == "{}":
            raise HclLoadError(f"Empty Variables File: {hcl_file_path}")
        return obj


def generate_table_for_file(hcl_file_path: str, default_value: str, output_buff):
    obj = load_hcl_file(hcl_file_path)
    return generate_table_for_tf_obj(obj, default_value, output_buff)


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
    print("| {} | {} | {} | {} |".format(
        "variable".ljust(col1),
        "default".ljust(col2),
        "required".ljust(col3),
        "description".ljust(col4)
    ), file=output_buff)
    print(
        "|-{}-|-{}-|-{}-|-{}-|".format("-" * col1, "-" * col2, "-" * col3, "-" * col4),
        file=output_buff
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

        print("| {} | {} | {} | {} |".format(
            str(key).strip(" ").ljust(col1),
            str(default).strip(" ").ljust(col2),
            str(required).strip(" ").ljust(col3),
            str(description).strip(" ").ljust(col4)
        ), file=output_buff)


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
            hcl_file_path=file_path,
            default_value=default_value,
            output_buff=sys.stdout
        )
    except HclLoadError as hclerr:
        print(f"{hclerr}", file=sys.stderr)


if __name__ == "__main__":
    main()
