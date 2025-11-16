"""
Algorithm-only entrypoint. Starts background runtime without FastAPI.
"""

from Base.runtime_runner import run_runtime_forever


def main():
    run_runtime_forever(logger_name="算法")


if __name__ == "__main__":
    main()
