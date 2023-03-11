import argparse
import os
import sys

import openai


def get_function_name(code):
    """
    Extract function name from a line beginning with "def "
    """
    if code.startswith("def "):
        return code[len("def "): code.index("(")]
    elif code.startswith("    def "):
        return code[len("    def "): code.index("(")]
    else:
        raise ValueError("Not a function definition: " + code)


def get_function_until_next(all_lines, i) -> str:
    ret = [all_lines[i]]
    for j in range(i + 1, i + 10000):
        if j < len(all_lines):
            if "def " in all_lines[j]:
                break
            else:
                ret.append(all_lines[j])
    return "\n".join(ret)


def get_functions(filepath):
    whole_code = open(filepath).read().replace("\r", "\n")
    all_lines = whole_code.split("\n")
    c = "no"
    for i, l in enumerate(all_lines):
        if l.startswith("class "):
            c = l[len("class "):]
        if l.strip().startswith("def"):
            code = get_function_until_next(all_lines, i)
            function_name = get_function_name(code)
            yield {"class": c, "code": code, "name": function_name, "filepath": filepath}


def generate_function_prompt(name: str = "no"):
    return ("You are a helpful assistant that writes docstrings for Python functions.\n" +
            "User will send you a function definition. Belonging to %s class\n" % name +
            "You'll respond with only a multi-line docstring to every function user sends. Dont append the start and ending triple quotes. \n" +
            "First part of the docstring is a description of functionality. Use function body to generate this description.\n" +
            "Second part of the docstring is a description of signature and return values.\n"
            "The second part should follow the rules of following format:\n" +
            ":param [ParamName]: [ParamDescription], defaults to [DefaultParamVal]\n:type [ParamName]: [ParamType](, optional)\n...\n:raises [ErrorType]: [ErrorDescription]\n...\n:return: [ReturnDescription]\n:rtype: [ReturnType]\n" +
            "Mark parameters as optional only if they have a default value.\n" +
            "Omit raises from the docstring if they don't occur.\n")

def generate_class_prompt(name: str = "no"):
    if name == "no":
        raise ValueError("Class name is required")
    return ("You are a helpful assistant that writes docstrings for Python classes.\n" +
            "User will send you a class constructor definition. Belonging to %s class\n" % name +
            "You'll respond with only a multi-line docstring to every class user sends the constructor for. Dont append the start and ending triple quotes. \n" +
            "First part of the docstring is a description of the class. Use class name and constructor body to generate this description.\n" +
            "Second part of the docstring is a description of signature and errors (if any) raised by the constructor.\n"
            "The second part should follow the rules of following format:\n" +
            ":param [ParamName]: [ParamDescription], defaults to [DefaultParamVal]\n:type [ParamName]: [ParamType](, optional)\n...\n:raises [ErrorType]: [ErrorDescription]\n...\n" +
            "Mark parameters as optional only if they have a default value.\n" +
            "Omit raises from the docstring if they don't occur.\n")


def get_docstring(function):
    if function["name"] == "__init__":
        prompt = generate_class_prompt(function["class"])
    else:
        prompt = generate_function_prompt(function["class"])
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": function["code"]},
        ],
        temperature=0
    )
    return completion["choices"][0]["message"]["content"]


def dump_docstring(f, indent, docstring):
    for i in range(2 * indent):
        f.write(" ")
    f.write("\"\"\"\n")
    doc_lines = docstring.split("\n")
    for l in doc_lines:
        for i in range(2 * indent):
            f.write(" ")
        f.write(l + "\n")
    for i in range(2 * indent):
        f.write(" ")
    f.write("\"\"\"\n")


def dump_code(new_file, original_file):
    with open(new_file, "w") as f:
        whole_code = open(original_file).read().replace("\r", "\n")
        all_lines = whole_code.split("\n")
        for i, l in enumerate(all_lines):
            if l.strip().startswith("def"):
                break

            f.write(l)
            f.write("\n")

        for func in all_functions:
            if func["name"] == "__init__" and func["name"] in docstrings:
                dump_docstring(f, code[0].index("def "), docstrings[func["name"]])
            code = func["code"].split("\n")
            indent = None
            in_header = True
            for line in code:
                if indent is None:
                    indent = line.index("def ")
                if in_header and line.strip() != '':
                    f.write(line + "\n")
                    if line.strip().endswith(':'):
                        in_header = False
                        if func["name"] != "__init__" and func["name"] in docstrings:
                            dump_docstring(f, indent, docstrings[func["name"]])
                elif not in_header:
                    f.write(line + "\n")


if __name__ == '__main__':
    openai.api_key = "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"

    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--folder", required=True, help="Folder to generate docs for")
    parser.add_argument("-l", "--location", required=True, help="Folder to place the newly generated files")
    args = parser.parse_args()

    if not os.path.exists(args.folder):
        print(f"Folder {args.file} does not exist")
        sys.exit(1)

    if not os.path.exists(args.location):
        os.makedirs(args.location)

    for file in os.listdir(args.folder):
        if file.endswith(".py") and not file.startswith("test_"):
            original = os.path.join(args.folder, file)
            print("Processing file " + original)
            all_functions = list(get_functions(original))
            docstrings = {}
            for i in all_functions:
                if "__" in i["name"] and not i["name"].startswith("__init__"):
                    continue
                docstrings[i["name"]] = get_docstring(i)
                print("Got docstring for " + i["name"])
            dump_code(os.path.join(args.location, file), original)



