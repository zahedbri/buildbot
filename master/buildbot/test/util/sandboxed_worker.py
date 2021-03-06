# This file is part of Buildbot.  Buildbot is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# Copyright Buildbot Team Members

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from subprocess import check_call

from twisted.internet import defer
from twisted.internet import protocol
from twisted.internet import reactor

from buildbot.util.service import AsyncService


class WorkerProcessProtocol(protocol.ProcessProtocol):
    def __init__(self):
        self.finished_deferred = defer.Deferred()

    def outReceived(self, data):
        print(data)

    def errReceived(self, data):
        print(data)

    def processEnded(self, _):
        self.finished_deferred.callback(None)

    def waitForFinish(self):
        return self.finished_deferred


class SandboxedWorker(AsyncService):
    def __init__(self, masterhost, port, name, passwd, workerdir, sandboxed_worker_path):
        self.masterhost = masterhost
        self.port = port
        self.workername = name
        self.workerpasswd = passwd
        self.workerdir = workerdir
        self.sandboxed_worker_path = sandboxed_worker_path

    def startService(self):

        # Note that we create the worker with sync API
        # We don't really care as we are in tests
        check_call([self.sandboxed_worker_path, "create-worker", '-q', self.workerdir,
                    self.masterhost + ":" + str(self.port), self.workername, self.workerpasswd])

        self.processprotocol = processProtocol = WorkerProcessProtocol()
        # we need to spawn the worker asynchronously though
        self.process = reactor.spawnProcess(
            processProtocol, self.sandboxed_worker_path, args=['bbw', 'start', '--nodaemon', self.workerdir])

        self.worker = self.master.workers.getWorkerByName(self.workername)
        return AsyncService.startService(self)

    @defer.inlineCallbacks
    def shutdownWorker(self):
        # on windows, we killing a process does not work well.
        # we use the graceful shutdown feature of buildbot-worker instead to kill the worker
        # but we must do that before the master is stopping.
        yield self.worker.shutdown()
        # wait for process to disappear
        yield self.processprotocol.waitForFinish()

    def stopService(self):
        return AsyncService.stopService(self)
