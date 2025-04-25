


LOGIN_WORKER_QUEUE = "login-worker-queue"
PORTUGAL_WORKER_QUEUE = "portugal-worker-queue"


QUEUES: set[str] = {
    LOGIN_WORKER_QUEUE,
    PORTUGAL_WORKER_QUEUE,
}
