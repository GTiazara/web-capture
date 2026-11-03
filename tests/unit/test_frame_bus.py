import asyncio

from tests.fakes import S
from web_capture.application.delivery import AllPolicy, LatestPolicy
from web_capture.application.frame_bus import FrameBus
from web_capture.domain.frame import Frame, FrameMetadata, Point, Size, Zone


def frame(seq: int) -> Frame:
    meta = FrameMetadata(
        seq=seq,
        ts_mono_ns=seq * S,
        ts_wall_ms=seq * 1000,
        capture_ms=1.0,
        tab_id="T",
        zone=Zone(0, 0, 10, 10),
        dpr=1.0,
        scroll=Point(0, 0),
        size=Size(10, 10),
    )
    return Frame(b"x", meta)


def publish(bus: FrameBus, seqs: range) -> None:
    for s in seqs:
        bus.publish(frame(s))


def test_eviction_keeps_most_recent() -> None:
    bus = FrameBus(3)
    publish(bus, range(4))
    assert [f.seq for f in bus.frames()] == [1, 2, 3]
    assert bus.get(0) is None
    assert bus.get(2) is not None


async def test_latest_policy_returns_most_recent_without_queue() -> None:
    bus = FrameBus(60)
    sub = bus.subscribe(LatestPolicy())
    publish(bus, range(10))
    d = await sub.next()
    assert d is not None and d.frame.seq == 9 and d.dropped == 0
    publish(bus, range(10, 13))
    d = await sub.next()
    assert d is not None and d.frame.seq == 12


async def test_latest_waits_for_newer_frame() -> None:
    bus = FrameBus(5)
    sub = bus.subscribe(LatestPolicy())
    publish(bus, range(1))
    assert (await sub.next()) is not None
    task = asyncio.create_task(sub.next())
    await asyncio.sleep(0)
    assert not task.done()
    bus.publish(frame(1))
    d = await asyncio.wait_for(task, 1)
    assert d is not None and d.frame.seq == 1


async def test_all_policy_sequential_then_dropped_after_lag() -> None:
    bus = FrameBus(60)
    sub = bus.subscribe(AllPolicy())
    publish(bus, range(1))
    d = await sub.next()
    assert d is not None and (d.frame.seq, d.dropped) == (0, 0)
    publish(bus, range(1, 4))
    got = [(await sub.next()) for _ in range(3)]
    assert [(x.frame.seq, x.dropped) for x in got if x] == [(1, 0), (2, 0), (3, 0)]
    publish(bus, range(4, 104))
    d = await sub.next()
    assert d is not None and d.frame.seq == 44 and d.dropped == 40
    d = await sub.next()
    assert d is not None and (d.frame.seq, d.dropped) == (45, 0)


async def test_all_policy_lag_of_100_with_capacity_60_reports_40() -> None:
    bus = FrameBus(60)
    sub = bus.subscribe(AllPolicy())
    bus.publish(frame(0))
    await sub.next()
    publish(bus, range(1, 101))
    d = await sub.next()
    assert d is not None and d.frame.seq == 41 and d.dropped == 40


def test_producer_never_blocks_and_memory_is_bounded() -> None:
    bus = FrameBus(60)
    bus.subscribe(AllPolicy())
    bus.subscribe(LatestPolicy())
    publish(bus, range(10_000))
    assert len(bus.frames()) == 60


async def test_close_wakes_waiting_subscribers() -> None:
    bus = FrameBus(5)
    sub = bus.subscribe(LatestPolicy())
    task = asyncio.create_task(sub.next())
    await asyncio.sleep(0)
    bus.close()
    assert await asyncio.wait_for(task, 1) is None


def test_subscriber_counts() -> None:
    bus = FrameBus(5)
    a = bus.subscribe(LatestPolicy())
    bus.subscribe(LatestPolicy())
    bus.subscribe(AllPolicy())
    assert bus.subscriber_counts() == {"latest": 2, "all": 1}
    a.close()
    a.close()
    assert bus.subscriber_counts() == {"latest": 1, "all": 1}
