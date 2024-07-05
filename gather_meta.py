import os
import json


def generate_json(directory):
    result = {"path": os.path.basename(directory), "list": [], "files": []}

    metainfo_path = os.path.join(directory, "metainfo.json")
    if os.path.isfile(metainfo_path):
        with open(metainfo_path, "r") as metainfo_file:
            result = sort_json_fields({**result, **dict(json.load(metainfo_file))})

    for entry in os.scandir(directory):
        if entry.is_dir() and entry.name != ".git" and entry.name != ".github":
            result["list"].append(generate_json(entry.path))
        elif entry.is_file() and entry.name != "metainfo.json":
            result["files"].append(entry.name)

    if not result["list"]:
        del result["list"]
    if not result["files"]:
        del result["files"]

    return result


def custom_sort(item):
    key, value = item
    # 将列表放在最后，其余字段按字母顺序排序
    if isinstance(value, list):
        return 4
    if key=="name":
        return 0
    if key=="description":
        return 1
    if key=="version":
        return 2
    return 3


def sort_json_fields(json_obj):
    # 对JSON对象的字段进行排序
    sorted_items = sorted(json_obj.items(), key=custom_sort)
    # 构建一个新的有序字典
    sorted_json_obj = {k: v for k, v in sorted_items}
    return sorted_json_obj

def main():
    directory = "."  # Starting from the current directory
    output_file = "extensions.json"

    json_structure = generate_json(directory)

    # Remove the top-level directory ('.')
    if json_structure["path"] == "." and "list" in json_structure:
        json_structure = json_structure["list"]
    
    

    with open(output_file, "w") as f:
        json.dump(json_structure, f, indent=4)

    print(f"JSON structure has been written to {output_file}")


if __name__ == "__main__":
    main()
