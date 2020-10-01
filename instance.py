#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @Time : 2020/9/25 20:14
# Author: Zheng Shaoxiang
# @Email : zhengsx95@163.com
# Description:
from collections import namedtuple
Item = namedtuple("Item", "id width")


class Instance:
    def __init__(self, file_name=None):
        self.capacity = None
        self.n = None
        self.items = None
        if file_name is not None:
            self.load_file(file_name)
        else:
            # todo: generate random instance
            pass

    def load_file(self, file_name):
        self.items = []
        with open(file_name, 'r') as file:
            for i in range(2):
                line = file.readline()

            self.capacity, self.n = list(int(i) for i in line.strip().split('\t'))

            for i in range(2):
                file.readline()

            for i in range(1, self.n + 1):
                w = int(file.readline().strip())
                self.items.append(Item(id=i, width=w))

    def __repr__(self):
        return f"capacity={self.capacity}\nitems={self.items}"


if __name__ == '__main__':
    pass
