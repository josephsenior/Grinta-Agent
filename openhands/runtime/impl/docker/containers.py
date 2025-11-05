import docker


def stop_all_containers(prefix: str) -> None:
    """Stop all Docker containers with names matching the given prefix.
    
    Silently handles API errors and missing containers.
    
    Args:
        prefix: Container name prefix to match
    """
    docker_client = docker.from_env()
    try:
        containers = docker_client.containers.list(all=True)
        for container in containers:
            try:
                if container.name.startswith(prefix):
                    container.stop()
            except docker.errors.APIError:
                pass
            except docker.errors.NotFound:
                pass
    except docker.errors.NotFound:
        pass
    finally:
        docker_client.close()
