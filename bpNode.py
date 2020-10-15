#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @Time : 2020/9/25 20:55
# Author: Zheng Shaoxiang
# @Email : zhengsx95@163.com
# Description:
from uti import ComparisonEpsilon
import copy


class Node:
    def __init__(self, rmp, level=0, **kwargs):
        self.rmp = rmp  # 限制主问题 Restricted master problem
        self.level = level  # 分支定界数中所在的层次，root在level 0

        # p = {(id1, id2): {1, 2,},...}存储所有同时包含这两个items的列序号
        # q = {(id1, id2): {1, 2,},...}存储所有仅包含这两个items其中之一的列序号
        self.p, self.q = kwargs.get("p", {}), kwargs.get("q", {})
        self.solution = kwargs.get("solution", None)

    def __copy__(self):
        return Node(copy.copy(self.rmp), p=copy.deepcopy(self.p), q=copy.deepcopy(self.q),
                    solution=self.solution)

    def get_solution(self):
        if self.solution is None:
            raise AttributeError("solution is None")
        return self.solution.solutions

    def update_param(self, coe):

        for c in coe:
            self.update_pq(c)

    def update_pq(self, coe):

        items = self.rmp.data.items
        var_num = self.rmp.var_num
        for i, item in enumerate(items):
            for j, _item in enumerate(items):
                if i < j:
                    if coe[i] == 1 and coe[j] == 1:
                        if self.p.get((item.id, _item.id), None) is None:
                            self.p[item.id, _item.id] = {var_num + 1}
                        else:
                            self.p[item.id, _item.id].add(var_num + 1)
                    elif coe[i] + coe[j] == 1:
                        if self.q.get((item.id, _item.id), None) is None:
                            self.q[item.id, _item.id] = {var_num + 1}
                        else:
                            self.q[item.id, _item.id].add(var_num + 1)

    def __le__(self, other):
        return self.solution.value <= other.solution.value + ComparisonEpsilon

    def __ge__(self, other):
        return self.solution.value + ComparisonEpsilon >= other.solution.value

    def __gt__(self, other):
        return not self.__le__(other)

    def __lt__(self, other):
        return not self.__ge__(other)


if __name__ == '__main__':
    pass
