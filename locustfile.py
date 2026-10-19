from locust import HttpUser, task, between

class AIServiceUser(HttpUser):
    wait_time = between(0.2, 1.0)

    @task
    def health(self):
        self.client.get("/health")
