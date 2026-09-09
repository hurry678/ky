"""Windows stub for the Unix-only `resource` module.

vec2text/experiments.py:317 只用到 resource.setrlimit(RLIMIT_CORE, ...)，
作用是解除 core dump 大小限制。Windows 无此概念，置为 no-op。
放在实验目录而非 site-packages，仅对本目录下运行的脚本生效。
"""

RLIMIT_CORE = 4
RLIM_INFINITY = -1


def setrlimit(resource_id, limits):  # no-op on Windows
    return None


def getrlimit(resource_id):
    return (RLIM_INFINITY, RLIM_INFINITY)
