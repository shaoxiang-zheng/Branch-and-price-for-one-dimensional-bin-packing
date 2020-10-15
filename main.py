#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @Time : 2020/9/25 20:13
# Author: Zheng Shaoxiang
# @Email : zhengsx95@163.com
# Description:
# 一维装箱问题(One-dimensional bin packing problem, 1D-BPP)问题的
# 分支定价算法(Branch and Price, BP)
from instance import Instance
import basicmodel
from searchTree import SearchTree

if __name__ == '__main__':
    instance = Instance()  # 读取文件生成1D-BPP实例
    print(f"{instance=}")

    bp = basicmodel.BinPacking({item.id: item for item in instance.items}, instance.capacity)

    m = bp.solve()
    bp.print_variables()
    print(f"{m.Runtime=}\t{m.objVal=}")
    print(f"-" * 60)
    tree = SearchTree(instance, verbose=True)  # 初始化搜索树
    tree.solve()
