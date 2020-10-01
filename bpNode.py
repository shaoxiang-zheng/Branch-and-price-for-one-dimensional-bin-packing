#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @Time : 2020/9/25 20:55
# Author: Zheng Shaoxiang
# @Email : zhengsx95@163.com
# Description:
from uti import ComparisonEpsilon


class Node:
    def __init__(self, rmp, level=0, **kwargs):
        self.rmp = rmp  # 限制主问题 Restricted master problem
        self.level = level  # 分支定界数中所在的层次，root在level 0

        # p = {(id1, id2): {1, 2,},...}存储所有同时包含这两个items的列序号
        # q = {(id1, id2): {1, 2,},...}存储所有仅包含这两个items其中之一的列序号
        self.p, self.q = kwargs.get("p", {}), kwargs.get("q", {})
        self.solution = None

    def get_solution(self):
        if self.solution is None:
            raise AttributeError("solution is None")
        return self.solution.solutions

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

    def should_be_pruned(self, incumbent):
        # 没有前途的结点，其松弛下界不小于当前存在的最好解（如果存在）
        if incumbent.value is not None and incumbent.value <= self.solution.value:
            return True

        # 如果该节点是可行的，则更新结点(如果该结点更好)
        if self.solution.is_integer_solution():
            incumbent.update(self.solution)
            return True

        return False

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
