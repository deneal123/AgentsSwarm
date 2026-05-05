from contextlib import asynccontextmanager


class FakeResult:
    def __init__(self, first=None, all=None):
        self._first = first
        self._all = all or []
        self.rowcount = None

    def first(self):
        return self._first

    def fetchall(self):
        return self._all


class FakeDBSession:
    """Generic fake async DB session used in unit tests.

    Provide mappings for query substring -> single row (first) or -> list (all).
    """

    def __init__(self, first_map=None, all_map=None):
        # first_map: dict of substring -> row
        # all_map: dict of substring -> list
        self.first_map = first_map or {}
        self.all_map = all_map or {}
        self.executed = []
        self._committed = False
        self._rolled_back = False
        # mapping of sql-substring -> rowcount to simulate conditional updates
        self.update_rowcounts = {}

    async def execute(self, sql, params=None):
        s = str(sql)
        self.executed.append((s, params))

        # check all_map first
        for key, val in self.all_map.items():
            if key in s:
                return FakeResult(all=val)

        for key, val in self.first_map.items():
            if key in s:
                return FakeResult(first=val)

        # If this is an UPDATE and we have configured rowcounts, attach it
        res = FakeResult()
        for key, rc in getattr(self, "update_rowcounts", {}).items():
            if key in s:
                res.rowcount = rc
                break
        return res

    async def commit(self):
        self._committed = True

    async def rollback(self):
        self._rolled_back = True

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeConnector:
    def __init__(self, session: FakeDBSession):
        self._session = session

    def get_session_context(self):
        @asynccontextmanager
        async def _ctx():
            yield self._session

        return _ctx()


class FakeRedis:
    def __init__(self):
        self.published = []

    def xadd(self, key, mapping):
        self.published.append((key, mapping))

    def close(self):
        pass


class FakeAsyncRedis:
    def __init__(self):
        self._called = 0
        self.published = []

    async def xread(self, streams, block=0, count=1):
        # override in test to provide behavior
        return []

    async def xread_group(self, group, consumer, streams=None, count=1, timeout=0):
        # delegate to xread by mapping params
        return await self.xread(streams or {}, block=timeout, count=count)

    async def xack(self, stream, group, message_id):
        # record ack for inspection if needed
        self.published.append(("ACK", stream, group, message_id))

    async def xautoclaim(self, *args, **kwargs):
        return []

    async def xauto_claim(self, *args, **kwargs):
        return []
