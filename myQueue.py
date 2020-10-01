#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @Time : 2020/9/25 20:13
# Author: Zheng Shaoxiang
# @Email : zhengsx95@163.com
# Description:
import heapq
from collections import deque


class MyQueue:
    def __init__(self, strategy="depth"):
        self.strategy = strategy
        self.aux = []
        if strategy == 'breadth':  # 广度优先搜索
            self.data = deque()
        elif strategy == 'depth':  # 深度优先策略
            self.data = deque()
        elif strategy == 'best':  # 最佳适应度优先
            self.data = []
        else:
            raise ValueError("The optional parameter 'strategy' should"
                             "be one of 'breadth', 'depth' and 'best'!")

    def push(self, item):
        if self.strategy == 'breadth':
            self.data.append(item)
        elif self.strategy == 'depth':
            self.data.append(item)
        else:
            heapq.heappush(self.data, item)

    def pop(self):
        if self.empty():
            raise ValueError("The queue is empty!")

        if self.strategy == 'breadth':
            return self.data.popleft()
        elif self.strategy == 'depth':
            while len(self.data) != 0:
                self.aux.append(self.data.pop())
            return self.aux.pop()
        else:
            heapq.heappop(self.data)

    def empty(self):
        if len(self.data) == 0 and len(self.aux) == 0:
            return True
        return False

    def size(self):
        return self.__len__()

    def __len__(self):
        return len(self.data) + len(self.aux)


if __name__ == '__main__':
    pass
