"""运行前的静态检查。

它能很快拒绝明显不合规的代码，并把原因告诉模型去修改，但不是安全边界：
Python 的静态检查总有办法绕过，真正的隔离靠渲染容器。
这里不依赖 Manim，API 服务也能直接用。
"""

import ast

MAX_BYTES = 40_000
BANNED_NAMES = {
    "__import__", "breakpoint", "compile", "delattr", "dir", "eval", "exec", "exit", "getattr", "globals",
    "hasattr", "help", "input", "locals", "memoryview", "object", "open", "quit", "setattr", "super", "type", "vars",
}
# clock 和 index 会让画面依赖动画时间，配音后时长一变就错；format 可以绕过下划线检查
BANNED_ATTRIBUTES = {"clock", "format", "format_map", "index"}
ALLOWED_NODES = (
    ast.Module, ast.Expr, ast.Assign, ast.AugAssign, ast.Import, ast.ImportFrom, ast.alias, ast.Pass,
    ast.If, ast.For, ast.FunctionDef, ast.arguments, ast.arg, ast.Return, ast.Lambda,
    ast.Name, ast.Constant, ast.Attribute, ast.Subscript, ast.Slice, ast.Call, ast.keyword,
    ast.Tuple, ast.List, ast.Dict, ast.Set, ast.Starred, ast.ListComp, ast.GeneratorExp, ast.DictComp,
    ast.comprehension,
    ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare, ast.IfExp, ast.JoinedStr, ast.FormattedValue,
    ast.operator, ast.unaryop, ast.boolop, ast.cmpop, ast.expr_context,
)


def check_code(code):
    """返回问题列表，每项是 {"line": 行号, "message": 原因}。列表为空表示通过。"""
    if len(code.encode("utf-8")) > MAX_BYTES:
        return [{"line": 0, "message": f"代码超过 {MAX_BYTES} 字节"}]
    try:
        tree = ast.parse(code)
    except SyntaxError as error:
        return [{"line": error.lineno or 0, "message": f"语法错误：{error.msg}"}]

    problems = []

    def report(node, message):
        problems.append({"line": getattr(node, "lineno", 0), "message": message})

    for node in ast.walk(tree):
        if not isinstance(node, ALLOWED_NODES):
            report(node, f"不允许使用 {type(node).__name__} 语法")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name != "math":
                    report(node, f"不允许 import {alias.name}。零件库要写成 from physkit import *，另外只能 import math")
        elif isinstance(node, ast.ImportFrom):
            # physkit 只能星号导入：它只公开零件，点进子模块就能碰到 os 这些内部依赖
            is_kit = node.module == "physkit" and [alias.name for alias in node.names] == ["*"]
            if node.level or not (is_kit or node.module == "math"):
                report(node, f"不允许这样导入 {node.module}。零件库要写成 from physkit import *，另外只能用 math")
        elif isinstance(node, ast.Name):
            if node.id in BANNED_NAMES or node.id.startswith("_"):
                report(node, f"不允许使用名字 {node.id}")
        elif isinstance(node, ast.Attribute):
            if node.attr.startswith("_") or node.attr in BANNED_ATTRIBUTES:
                report(node, f"不允许访问属性 {node.attr}")
        elif isinstance(node, ast.Constant):
            if isinstance(node.value, (str, bytes)) and ("__" in str(node.value)):
                report(node, "字符串里不允许出现双下划线")
        elif isinstance(node, (ast.FunctionDef, ast.arg, ast.keyword, ast.alias)):
            name = getattr(node, "name", None) or getattr(node, "arg", None)
            if name and name.startswith("_"):
                report(node, f"不允许使用名字 {name}")

    assigned = {
        target.id
        for node in tree.body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    }
    for required in ("timeline", "stage"):
        if required not in assigned:
            problems.append({"line": 0, "message": f"代码顶层必须定义变量 {required}"})
    return problems
