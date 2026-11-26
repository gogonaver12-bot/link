"""Hugging Face Space 호출 공통: 한 번에 최대 N초만 기다리고(대기 줄에 갇혀 45분 실행 제한에 걸리지 않게),
전체 사용 시간 예산(AI_TIME_BUDGET_MIN, 기본 20분)을 넘으면 더 부르지 않는다."""
import os
import time

_start = time.time()


def budget_left():
    return (float(os.getenv("AI_TIME_BUDGET_MIN", "20")) * 60) - (time.time() - _start)


def predict(space, api_name, kw, timeout=300):
    from gradio_client import Client
    left = budget_left()
    if left < 60:
        raise TimeoutError("AI 영상 시간 예산 끝")
    job = Client(space, token=os.getenv("HF_TOKEN") or None, verbose=False).submit(**kw, api_name=api_name)
    try:
        return job.result(timeout=min(timeout, left))
    except Exception:
        try:
            job.cancel()
        except Exception:
            pass
        raise
