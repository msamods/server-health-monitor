from typing import List, Dict, Any, Optional

try:
    import docker
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False


def get_docker_client():
    """Attempt to get an active Docker client."""
    if not DOCKER_AVAILABLE:
        return None
    try:
        client = docker.from_env(timeout=3)
        client.ping()
        return client
    except Exception:
        return None


def get_docker_status() -> Dict[str, Any]:
    """Retrieve an overview of all Docker containers."""
    client = get_docker_client()
    if not client:
        return {
            "available": False,
            "message": "Docker daemon is not running or not accessible."
        }

    try:
        containers = client.containers.list(all=True)
        running = [c for c in containers if c.status == "running"]
        stopped = [c for c in containers if c.status != "running"]

        container_list = []
        for c in containers:
            image_name = c.image.tags[0] if c.image.tags else c.image.short_id
            container_list.append({
                "id": c.short_id,
                "name": c.name,
                "image": image_name,
                "status": c.status,
                "state": c.attrs.get("State", {}).get("Status", "unknown"),
            })

        return {
            "available": True,
            "total": len(containers),
            "running": len(running),
            "stopped": len(stopped),
            "containers": container_list,
        }
    except Exception as e:
        return {
            "available": False,
            "message": f"Docker error: {str(e)}"
        }


def restart_container(container_id_or_name: str) -> Dict[str, Any]:
    """Restart a specific container by name or short ID."""
    client = get_docker_client()
    if not client:
        return {"success": False, "message": "Docker is not available."}

    try:
        container = client.containers.get(container_id_or_name)
        container.restart(timeout=10)
        return {
            "success": True,
            "message": f"Container <b>{container.name}</b> restarted successfully."
        }
    except Exception as e:
        return {"success": False, "message": f"Failed to restart container: {str(e)}"}


def get_crashed_containers() -> List[Dict[str, str]]:
    """Find containers that exited with a non-zero exit code."""
    client = get_docker_client()
    if not client:
        return []

    crashed = []
    try:
        containers = client.containers.list(all=True)
        for c in containers:
            state = c.attrs.get("State", {})
            status = state.get("Status")
            exit_code = state.get("ExitCode", 0)
            if status in ("exited", "dead") and exit_code != 0:
                crashed.append({
                    "id": c.short_id,
                    "name": c.name,
                    "exit_code": exit_code,
                    "error": state.get("Error", "None"),
                })
    except Exception:
        pass
    return crashed
