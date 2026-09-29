import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]

files = ["docker-compose.yml", "docker/docker-compose.infra.yml"]
ok = True
for path in files:
    with (ROOT / path).open(encoding="utf-8") as handle:
        doc = yaml.safe_load(handle)
    services = doc.get("services", {})
    print(f"{path}: services={sorted(services)}")
    for name, service in services.items():
        if "image" not in service and "build" not in service:
            print(f"  ERROR: service {name} has no image or build")
            ok = False
    networks = doc.get("networks", {})
    print(f"  networks={list(networks)} volumes={list(doc.get('volumes', {}))}")

# Cross checks for the full stack
with (ROOT / "docker-compose.yml").open(encoding="utf-8") as handle:
    stack = yaml.safe_load(handle)
expected = {"frontend", "backend", "postgres", "hindsight"}
missing = expected - set(stack.get("services", {}))
if missing:
    print("ERROR: missing required services:", missing)
    ok = False
else:
    print("required services present:", sorted(expected))

backend_env = stack["services"]["backend"].get("environment", {})
if backend_env.get("HINDSIGHT_BASE_URL") != "http://hindsight:8888":
    print("ERROR: backend does not point at the hindsight service")
    ok = False
if "postgres" not in stack["services"]["backend"].get("depends_on", {}):
    print("ERROR: backend does not wait for postgres")
    ok = False
if "backend" not in stack["services"]["frontend"].get("depends_on", {}):
    print("ERROR: frontend does not wait for backend")
    ok = False

print("RESULT:", "OK" if ok else "FAILED")
sys.exit(0 if ok else 1)
