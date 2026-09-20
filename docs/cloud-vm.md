# Cloud VM Deployment

Aegis Forge can run on a small Linux VM with Docker and systemd while keeping Ollama on the same private network.

```bash
sudo apt-get update && sudo apt-get install -y docker.io docker-compose-plugin
sudo usermod -aG docker "$USER"
git clone https://github.com/gbemidaniel100-bot/Aegis_Forge aegis-forge
cd aegis-forge
docker compose up -d --build
curl http://127.0.0.1:8000/ready
```

Put TLS and authentication at a reverse proxy, set `AEGIS_API_TOKEN`, and expose only ports 80/443. The application has `/health` for liveness, `/ready` for dependency readiness, and the container receives Docker stop signals for graceful Uvicorn shutdown.

For a managed deployment, replace the local volume with encrypted persistent storage and export `/metrics` to the VM monitoring agent.
