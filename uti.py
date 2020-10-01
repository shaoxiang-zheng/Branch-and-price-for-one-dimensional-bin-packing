#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @Time: 2020/9/26 9:41
# Author: Zheng Shaoxiang
# @Email: zhengsx95@163.com
# Description:
from enum import Enum

ReducedEpsilon = 1e-5

IntegerEpsilon = 1e-6

ComparisonEpsilon = 1e-5


def is_integer(num):
    if abs(round(num) - num) <= IntegerEpsilon:
        return True
    return False


class Status(Enum):
    LOADED = 1
    OPTIMAL = 2
    INFEASIBLE = 3
    UNBOUNDED = 5
    CUTOFF = 6
    ITERATION_LIMIT = 7
    NODE_LIMIT = 8
    TIME_LIMIT = 9
    SOLUTION_LIMIT = 10
    INTERRUPTED = 11
    NUMERIC = 12
    SUBOPTIMAL = 13
    INPROGRESS = 14
    USER_OBJ_LIMIT = 15


if __name__ == '__main__':
    pass
