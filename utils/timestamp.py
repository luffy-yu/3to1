import time


def timestamp2frame(timestamp, fps):
    if not fps:
        return int(float(timestamp))
    return int(float(timestamp) * int(fps))


def frame2timestamp(frame, fps):
    pass


def get_time() -> float:
    return time.time()
