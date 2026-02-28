from locust import HttpUser, task, between
import random


class NGCLoadTestUser(HttpUser):
    # Base URL is expected to be http://127.0.0.1:8000

    # Wait time between requests for each user (simulates think time)
    wait_time = between(0.1, 0.5)

    @task(3)
    def query_chromosome(self):
        """Simulate a user filtering variants by a random chromosome"""
        # The chromosomes we used in our synthetic VCF
        chromosomes = ["1", "2", "3", "X", "Y"]
        chr_query = random.choice(chromosomes)

        # Secure API Header
        headers = {"Authorization": "Bearer ngc-secret-admin-token"}

        # Give the request a name in locust so they group cleanly by endpoint, not unique URL
        self.client.get(
            f"/variants?chr={chr_query}", headers=headers, name="/variants?chr=[random]"
        )

    @task(1)
    def query_dataset_list(self):
        """Simulate a user checking available datasets"""
        headers = {"Authorization": "Bearer ngc-secret-admin-token"}
        self.client.get("/datasets", headers=headers)

    @task(1)
    def health_check(self):
        """Simulate an infrastructure ping"""
        self.client.get("/health")
