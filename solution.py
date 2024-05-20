#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @Time : 2020/9/25 21:41
# Author: Zheng Shaoxiang
# @Email : zhengsx95@163.com
# Description:
from uti import is_integer, ComparisonEpsilon


class Solution:
    def __init__(self, value=None, solutions=None, model=None):
        self.value = value
        self.solutions = solutions
        self.model = model

    def output_solution(self):
        pass

    def update(self, other):
        # 当other代表的解是整数可行解，判断更新当前解
        if self.value is None or \
                other.value < self.value + ComparisonEpsilon:
            self.value, self.solutions = other.value, other.solutions
            self.model = other.model

    def is_integer_solution(self):
        for s in self.solutions.values():
            if not is_integer(s):
                return False
        return True

    def __repr__(self):
        return f"value={self.value}\nsolutions={self.solutions}"


if __name__ == '__main__':
    pass
