#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @Time : 2020/9/25 21:50
# Author: Zheng Shaoxiang
# @Email : zhengsx95@163.com
# Description:
from uti import ReducedEpsilon
from uti import Status
from solution import Solution


class ColumnGeneration:
    def __init__(self, node):
        self.node = node
        self.rmp = node.rmp

    def solve(self):
        while True:
            self.rmp.optimize()   # 单纯形法求解该模型

            assert self.rmp.get_status() != Status.INFEASIBLE

            # 判断是否存在reduced cost 小于0 的列
            # 1.获取两类约束对应的对偶变量
            ex_dual, sr_dual = self.rmp.get_dual()
            # 2.求解对应的定价问题
            self.rmp.optimize_pricing(ex_dual, sr_dual)
            # 3.获取reduced cost并判断
            reduced_cost = self.rmp.get_reduced_cost()
            if reduced_cost + ReducedEpsilon >= 0:  # reduced cost为正
                assert self.node.rmp is self.rmp
                return Solution(self.rmp.get_objVal(), self.rmp.getVars())  # 返回此时的RMP最优解

            # 4.此时存在reduced cost < 0的列，返回并在rmp中添加该列
            coe = self.rmp.get_pricing_coe()
            self.node.update_pq(coe)
            self.rmp.add_col(coe)


if __name__ == '__main__':
    pass
