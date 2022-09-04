#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @Time : 2020/9/25 20:13
# Author: Zheng Shaoxiang
# @Email : zhengsx95@163.com
# Description:
# 一维装箱问题(One-dimensional bin packing problem, 1D-BPP)问题的
# 分支定价算法(Branch and Price, BP)
import re

from instance import Instance
import basicmodel
from searchTree import SearchTree
import cProfile
import json

if __name__ == '__main__':
    instance = Instance('data.txt')  # 读取文件生成1D-BPP实例
    print(f"{instance=}")

    # bp = basicmodel.BinPacking({item.id: item for item in instance.items}, instance.capacity)
    #
    # m = bp.solve()
    # # bp.print_variables()
    # print(f"{m.Runtime=}\t{m.objVal=}")
    print(f"-" * 60)
    with open("js.json") as f:
        init_columns = list(json.load(f).values())
        # print(init_columns)
    tree = SearchTree(instance, verbose=True, init_columns=init_columns)  # 初始化搜索树
    tree.solve()

    rmp = tree.incumbent.model
    rmp.update()
    rmp.write("mip.lp")
    for name, v in tree.incumbent.solutions.items():
        if v > 0:
            print(name, v)

            column = {int(re.search(r"\d+", constr.constrName).group()): rmp.getCoeff(
                constr, rmp.getVarByName(name)) for constr in rmp.getConstrs() if constr.constrName.startswith('exact')}
            print(column, '\n')
    # cProfile.run('tree.solve()', sort=1)
