#!/bin/python3
import json
import re
import sys
import shlex


def substitute_variables(value, variables):
    # This function substitutes variables in the format ${var} with their corresponding values from the variables dictionary
    pattern = re.compile(r"\$\{([^}]+)\}")

    def replace(match):
        var_name = match.group(1)
        return variables.get(var_name, match.group(0))

    return pattern.sub(replace, value)


def parse_tokens(tokens):
    result = {}
    key = None
    inside_list = False
    inside_function = False
    current_list = []

    token_iter = iter(tokens)

    for token in token_iter:
        if inside_function:
            if token == "}":
                inside_function = False
            continue

        if token == "=":
            continue

        elif token == "(":
            next_token = next(token_iter)
            if key and next_token == ")" and next(token_iter) == "{":
                inside_function = True
                continue
            inside_list = True
            current_list = []
            if next_token != ")":
                current_list.append(next_token)

        elif token == ")":
            inside_list = False
            result[key] = current_list
            key = None

        elif token == "{":
            # Start of a function, skip until the matching '}'
            inside_function = True

        else:
            if inside_list:
                current_list.append(token)
            else:
                if key is None:
                    key = token
                else:
                    result[key] = token
                    key = None

    for k, v in result.items():
        if isinstance(v, list):
            result[k] = [substitute_variables(item, result) for item in v]
        else:
            result[k] = substitute_variables(v, result)
    return result


def parse_script(script):
    lexer = shlex.shlex(script, posix=True)
    lexer.wordchars += "/.+-_"
    return parse_tokens(lexer)



if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <filename>")
    else:
        with open(sys.argv[1]) as f:
            result = parse_script(f.read())
            print(
                json.dumps(
                    result,
                    indent=4,
                    separators=(", ", ": "),
                    ensure_ascii=False,
                )
            )