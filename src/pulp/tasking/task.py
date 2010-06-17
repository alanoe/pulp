#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright © 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

_author_ = 'Jason L Connor <jconnor@redhat.com>'

import datetime
import sys
import time
import traceback
import uuid

from pulp.model import Base
from pulp.tasking.queue.base import SimpleTaskQueue

# task states -----------------------------------------------------------------

task_created = 'created'
task_reset = 'reset'
task_waiting = 'waiting'
task_running = 'running'
task_finished = 'finished'
task_error = 'error'

task_states = (
    task_created,
    task_waiting,
    task_running,
    task_finished,
    task_error,
    task_reset,
)

task_ready_states = (
    task_created,
    task_waiting,
    task_reset,
)

task_complete_states = (
    task_finished,
    task_error,
)

# task ------------------------------------------------------------------------
    
class Task(object):
    """
    Task class
    Meta data for executing a long-running task.
    """
    def __init__(self, callable, *args, **kwargs):
        """
        Create a Task for the passed in callable and arguments.
        @param callable: function, method, lambda, or object with __call__
        @param args: positional arguments to be passed into the callable
        @param kwargs: keyword arguments to be passed into the callable
        """
        self.id = str(uuid.uuid1(clock_seq=int(time.time() * 1000)))
        self.callable = callable
        self.args = args
        self.kwargs = kwargs
        self.queue = SimpleTaskQueue()
        
        self.method_name = callable.__name__
        self.state = task_created
        self.start_time = None
        self.finish_time = None
        self.next_time = None
        self.result = None
        self.exception = None
        self.traceback = None

    def waiting(self):
        """
        Mark this task as waiting
        """
        assert self.state in task_ready_states
        self.state = task_waiting
        
    def running(self):
        """
        Mark this task as running
        """
        assert self.state in task_ready_states
        self.state = task_running
        
    def run(self):
        """
        Run this task and record the result or exception
        """
        self.start_time = datetime.datetime.now()
        try:
            result = self.callable(*self.args, **self.kwargs)
        except Exception, e:
            self.state = task_error
            self.exception = repr(e)
            # exc_info returns tuple (class, exception, traceback)
            # format_exception takes 3 arguments (class, exception, traceback)
            exc_info = sys.exc_info()
            self.traceback = traceback.format_exception(*exc_info)
        else:
            self.state = task_finished
            self.result = result
        self.finish_time = datetime.datetime.now()
        self.queue.complete(self)
        
    def reset(self):
        """
        Reset this task's recorded data
        """
        if self.state not in task_complete_states:
            return
        self.state = task_reset
        self.start_time = None
        self.finish_time = None
        self.next_time = None
        self.result = None
        self.exception = None
        self.traceback = None

# task model ------------------------------------------------------------------

class TaskModel(Base):
    """
    Task model class to enable storage of task state in the database
    """
    def __init__(self):
        self._id = None
        self.id = None
        
        self.method_name = None
        self.state = None
        self.start_time = None
        self.finish_time = None
        self.next_time = None
        self.result = None
        self.exception = None
        self.traceback = None
        

_common_attrs = (
    'id',
    'method_name',
    'state',
    'start_time',
    'finish_time',
    'next_time',
    'result',
    'exception',
    'traceback',
)
        

def task2model(task):
    model = TaskModel()
    model._id = task.id
    
    for attr in _common_attrs:
        value = getattr(task, attr)
        setattr(model, attr, value)
        
    return model