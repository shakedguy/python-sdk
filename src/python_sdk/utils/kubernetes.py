import os
from functools import cache


@cache
def is_running_in_kubernetes() -> bool:
    """
    Checks if the application is running inside a Kubernetes cluster.

    Returns:
        bool: True if running in Kubernetes, False otherwise.
    """
    # Check for Kubernetes-specific environment variables
    kubernetes_env_vars = ["KUBERNETES_SERVICE_HOST", "KUBERNETES_PORT"]

    if all(var in os.environ for var in kubernetes_env_vars):
        return True

    # Check for the presence of the Kubernetes service account token file
    service_account_token_path = "/var/run/secrets/kubernetes.io/serviceaccount/token"

    if os.path.exists(service_account_token_path):
        return True

    return False
