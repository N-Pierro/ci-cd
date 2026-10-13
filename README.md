# tasks-api

A small Flask REST API used as the target for a DevSecOps CI/CD lab.

## Layout
| Path | Purpose |
|---|---|
| `app/` | Flask application (app factory, models, routes) |
| `tests/` | pytest suite (coverage feeds SonarQube) |
| `Dockerfile` | Multi-stage, non-root, healthcheck |
| `infra/<env>/deployment.yaml` | Namespace, ServiceAccount, Deployment, Service per environment |
| `Jenkinsfile` | Pipeline: secrets scan, tests, SAST, Sonar, build, Trivy, Harbor push, deploy |
| `sonar-project.properties` | SonarQube project settings |

## Run locally
    python3 -m venv .venv && . .venv/bin/activate
    pip install -r requirements-dev.txt
    pytest
    flask --app app:create_app run          # http://127.0.0.1:5000

## Run in Docker
    docker build -t tasks-api:local .
    docker run --rm -p 8000:8000 tasks-api:local
    curl localhost:8000/healthz
    curl -X POST localhost:8000/api/v1/tasks -H 'Content-Type: application/json' -d '{"title":"hello"}'

## Endpoints
`GET /healthz`, `GET /readyz`, `GET|POST /api/v1/tasks`, `GET|PATCH|DELETE /api/v1/tasks/<id>`

## Jenkins prerequisites
- Credentials: `sonar-token`, `vault-approle`, `kubeconfig-dev|staging|prod` (file)
- Tools: `sonar-scanner`; server name `sonarqube`
- Harbor project `myapp`; Vault secret `secret/myapp/harbor`
- Jenkins user can run `docker` and `kubectl`
- Pipeline type: **Multibranch** (the `when { branch 'main' }` conditions need it)
