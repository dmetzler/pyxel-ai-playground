# pyxel-ai-playground Helm chart

Deploys **Pyxel AI Playground** (FastAPI backend + nginx/React frontend) on Kubernetes,
protected by an [oauth2-proxy](https://oauth2-proxy.github.io/oauth2-proxy/) sidecar.

```
Ingress -> Service "http" (4180) -> frontend pod
             [oauth2-proxy :4180] -> [nginx :80, SPA + /api proxy] -> backend Service :8000 -> PVC /games
```

- The **backend** stores every game as a git repository under `/games` on a ReadWriteOnce
  PVC, so it always runs **1 replica** with a **Recreate** strategy. Probes use `GET /api/health`.
- The **frontend** nginx config is replaced by a chart ConfigMap that proxies `/api/` to the
  chart's backend Service, with `proxy_buffering off` (streamed tutor replies),
  `proxy_read_timeout 300s` and `client_max_body_size 60m`.
- **oauth2-proxy** runs with `--flush-interval=100ms` and `--upstream-timeout=300s` so
  server-sent events stream through. `auth.enabled=false` removes it (local tests only).
- Secrets are rendered into a chart Secret unless `existingSecret` is set. Changes to the
  Secret or nginx ConfigMap roll the pods (checksum annotations).

## Install

1. Register an OIDC client at your IdP with redirect URI `https://<host>/oauth2/callback`.
2. Generate a cookie secret: `openssl rand -base64 32 | tr -- '+/' '-_' | head -c 32`
3. Install:

```bash
# Keycloak
helm install pyxel charts/pyxel-ai-playground -n pyxel --create-namespace \
  --set ingress.enabled=true --set ingress.className=nginx \
  --set ingress.host=pyxel.example.com \
  --set 'ingress.tls[0].secretName=pyxel-tls' --set 'ingress.tls[0].hosts[0]=pyxel.example.com' \
  --set oauth2Proxy.issuerUrl=https://keycloak.example.com/realms/school \
  --set oauth2Proxy.clientId=pyxel \
  --set oauth2Proxy.clientSecret=<client-secret> \
  --set oauth2Proxy.cookieSecret=$(openssl rand -base64 32 | tr -- '+/' '-_' | head -c 32) \
  --set openai.baseUrl=http://litellm.litellm:4000 \
  --set openai.apiKey=<litellm-key> --set openai.model=claude-3-5-sonnet
```

For **Google**, use `--set oauth2Proxy.issuerUrl=https://accounts.google.com` with a Google
OAuth client, and restrict users with e.g. `--set 'oauth2Proxy.emailDomains={myschool.org}'`.

Using pre-created secrets instead:

```bash
kubectl -n pyxel create secret generic pyxel-oauth \
  --from-literal=client-id=pyxel --from-literal=client-secret=... --from-literal=cookie-secret=...
kubectl -n pyxel create secret generic pyxel-llm --from-literal=api-key=...
helm install pyxel charts/pyxel-ai-playground -n pyxel \
  --set oauth2Proxy.existingSecret=pyxel-oauth --set openai.existingSecret=pyxel-llm \
  --set oauth2Proxy.issuerUrl=https://keycloak.example.com/realms/school \
  --set ingress.enabled=true --set ingress.host=pyxel.example.com
```

Local test without authentication:

```bash
helm install pyxel charts/pyxel-ai-playground --set auth.enabled=false --set openai.apiKey=<key>
kubectl port-forward svc/pyxel-pyxel-ai-playground-frontend 8080:4180
```

## Values

| Key | Default | Description |
|---|---|---|
| `auth.enabled` | `true` | Run the oauth2-proxy sidecar; `false` points the Service at nginx directly |
| `oauth2Proxy.issuerUrl` | `""` | OIDC issuer URL of the IdP (**required** when auth enabled) |
| `oauth2Proxy.clientId` | `""` | OAuth client id (**required** unless `existingSecret`) |
| `oauth2Proxy.clientSecret` | `""` | OAuth client secret (**required** unless `existingSecret`) |
| `oauth2Proxy.cookieSecret` | `""` | 16/24/32-byte cookie secret (**required** unless `existingSecret`) |
| `oauth2Proxy.existingSecret` | `""` | Secret with keys `client-id`, `client-secret`, `cookie-secret` |
| `oauth2Proxy.provider` | `oidc` | oauth2-proxy provider |
| `oauth2Proxy.scopes` | `openid email profile` | Requested scopes |
| `oauth2Proxy.emailDomains` | `["*"]` | Allowed e-mail domains |
| `oauth2Proxy.allowedGroups` | `[]` | Allowed IdP groups (empty = any) |
| `oauth2Proxy.redirectUrl` | `""` | Callback URL; default `https://<ingress.host>/oauth2/callback` |
| `oauth2Proxy.extraArgs` | `[]` | Extra oauth2-proxy flags |
| `oauth2Proxy.image.*` | `quay.io/oauth2-proxy/oauth2-proxy:v7.15.5` | Sidecar image |
| `oauth2Proxy.resources` | `{}` | Sidecar resources |
| `openai.baseUrl` | `http://litellm:4000` | OpenAI-compatible endpoint (`LITELLM_BASE_URL`) |
| `openai.apiKey` | `""` | API key (`LITELLM_API_KEY`, **required** unless `existingSecret`) |
| `openai.model` | `claude-3-5-sonnet` | Model id (`LITELLM_MODEL`) |
| `openai.existingSecret` | `""` | Secret with key `api-key` |
| `maxTokens` | `16000` | `PIX_MAX_TOKENS` |
| `backend.image.*` | `ghcr.io/dmetzler/pyxel-ai-playground-backend`, tag = appVersion | Backend image |
| `backend.extraEnv` | `[]` | Extra backend env vars |
| `backend.resources` | `{}` | Backend resources |
| `frontend.image.*` | `ghcr.io/dmetzler/pyxel-ai-playground-frontend`, tag = appVersion | Frontend image |
| `frontend.replicas` | `1` | Frontend replicas |
| `frontend.resources` | `{}` | nginx resources |
| `persistence.enabled` | `true` | Use a PVC for `/games` (else emptyDir) |
| `persistence.size` | `5Gi` | PVC size |
| `persistence.storageClass` | `""` | Storage class (empty = default) |
| `persistence.existingClaim` | `""` | Use an existing PVC |
| `persistence.accessModes` | `[ReadWriteOnce]` | PVC access modes |
| `service.type` / `service.port` | `ClusterIP` / `4180` | Frontend Service |
| `ingress.enabled` | `false` | Create an Ingress |
| `ingress.className` | `""` | IngressClass |
| `ingress.host` | `""` | Public host name |
| `ingress.annotations` | ingress-nginx: buffering off, body 60m, read timeout 300 | Ingress annotations |
| `ingress.tls` | `[]` | TLS entries |
| `imagePullSecrets` | `[]` | Pull secrets |
| `podAnnotations` | `{}` | Extra pod annotations |
| `podSecurityContext` | `{}` | Pod security context for both pods |
| `nodeSelector` / `tolerations` / `affinity` | `{}` / `[]` / `{}` | Scheduling |

The PVC carries `helm.sh/resource-policy: keep`: `helm uninstall` does not delete the games.
