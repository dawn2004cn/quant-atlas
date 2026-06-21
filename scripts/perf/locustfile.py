from __future__ import annotations

from locust import HttpUser, between, task


class ApiSmokeUser(HttpUser):
    wait_time = between(0.1, 0.5)

    @task(3)
    def health(self) -> None:
        self.client.get("/api/v1/health")

    @task(1)
    def daily_workbench(self) -> None:
        self.client.get("/api/v1/daily-workbench")
