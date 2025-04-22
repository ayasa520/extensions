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
    function_braces_count = 0  # 用来跟踪嵌套的大括号
    current_list = []
    current_function_name = None

    token_iter = iter(tokens)

    for token in token_iter:
        # 处理函数内部的情况
        if inside_function:
            if token == "{":
                function_braces_count += 1
            elif token == "}":
                function_braces_count -= 1
                if function_braces_count == 0:  # 函数结束
                    inside_function = False
                    current_function_name = None
            continue  # 跳过函数内的所有内容

        if token == "=":
            continue

        elif token == "(":
            next_token = next(token_iter, None)
            if next_token is None:
                continue
                
            if key and next_token == ")":
                try:
                    next_brace = next(token_iter, None)
                    if next_brace == "{":
                        # 这是一个函数定义，比如 package() {
                        inside_function = True
                        function_braces_count = 1
                        current_function_name = key
                        key = None  # 重置 key，不保存函数名
                        continue
                    else:
                        # 不是函数，回退处理
                        inside_list = True
                        current_list = []
                except StopIteration:
                    pass
            else:
                inside_list = True
                current_list = []
                if next_token != ")":
                    current_list.append(next_token)

        elif token == ")":
            inside_list = False
            if key:  # 只有在有键的情况下才添加到结果
                result[key] = current_list
                key = None

        elif token == "{":
            # 可能是一个独立的函数块开始
            inside_function = True
            function_braces_count = 1

        else:
            if inside_list:
                current_list.append(token)
            else:
                if key is None:
                    key = token
                else:
                    result[key] = token
                    key = None

    # 变量替换
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