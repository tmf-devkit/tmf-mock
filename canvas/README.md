# tmf-mock on the local ODA Canvas - Stage 1a

This folder registers the existing `tmf-mock` container as an ODA Component
inside a local Canvas. The point is not to ship a production-grade component;
it is to learn - first-hand - what the Canvas operators actually do when you
give them a component manifest.

> **No tmf-mock source/image changes.** Everything here is declarative
> Kubernetes/ODA YAML against the published `mchavan23/tmf-mock:0.1.1`
> image. If Stage 1a goes wrong, nothing about the published mock changes.

## Files in this folder

| File | What it creates |
|---|---|
| `00-namespace.yaml`  | Namespace `components` with Istio sidecar injection enabled. |
| `10-deployment.yaml` | Deployment of `mchavan23/tmf-mock:0.1.1` (1 replica), env vars, probes on `/health`. |
| `11-service.yaml`    | ClusterIP `tmf-mock-svc` on port 8000. |
| `20-component.yaml`  | The ODA Component CRD - 3 exposed APIs (TMF638/639/641), no dependent APIs, minimal security. |
| `verify.cmd`         | Read-only verification - pod, component, ExposedAPIs, VirtualServices, smoke curl. |
| `README.md`          | This file. |

## Prerequisites

A working Canvas (per `ODA_Canvas_Setup_and_Architecture.md`):

- MiniKube running: `minikube start --cpus 4 --memory 16384 --driver docker`
- `minikube tunnel` running in a separate terminal
- Istio installed in `istio-system` + `istio-ingress`
- ODA Canvas installed in the `canvas` namespace with `canvas-vault.enabled=false`

Quick check:

```cmd
kubectl get nodes
kubectl get pods -n canvas
kubectl get svc -n istio-ingress istio-ingress
```

The last command should show an `EXTERNAL-IP` - not `<pending>`. If it is
pending, the `minikube tunnel` terminal is not running.

## Apply order

```cmd
cd C:\myclaude\tmf-mock\canvas

REM Dry-run first (server-side, validates against live CRD schemas).
kubectl apply --dry-run=server -f .

REM If dry-run is clean, apply for real.
kubectl apply -f .
```

Or one at a time:

```cmd
kubectl apply -f 00-namespace.yaml
kubectl apply -f 10-deployment.yaml
kubectl apply -f 11-service.yaml
kubectl apply -f 20-component.yaml
```

## What we expect to happen

1. **Namespace + Deployment + Service apply immediately.** Within ~30s the
   `tmf-mock` pod is Running and Ready.

2. **The Component manifest triggers the operator chain:**
   - `compcrdwebhook` validates the YAML against the v1 schema.
   - `component-operator` creates one **ExposedAPI** CRD per declared API:
     `tmf-devkit-mock-serviceinventory`, `tmf-devkit-mock-resourceinventory`,
     `tmf-devkit-mock-serviceordering`.
   - `api-operator-istio` creates one **Istio VirtualService** per ExposedAPI,
     routing the declared `path` -> `tmf-mock-svc:8000`.
   - `identityconfig-operator` processes `securityFunction`. Because we have
     not implemented TMF669 PartyRole, this is expected to produce a
     non-Ready condition. **That observation is the primary learning of**
     **Stage 1a - capture the condition message.**
   - `canvas-depapi-op` sees `dependentAPIs: []` and is a no-op.

3. **A curl through the Istio ingress reaches a real TMF endpoint:**

   The Canvas `component-gateway` is HTTPS-only - plain HTTP returns 404.
   Use HTTPS with `-k` to skip cert verification on the self-signed cert.

   ```cmd
   for /f "tokens=*" %i in ('kubectl get svc -n istio-ingress istio-ingress -o jsonpath^="{.status.loadBalancer.ingress[0].ip}"') do set INGRESS=%i
   curl -sSk "https://%INGRESS%/tmf-api/serviceInventoryManagement/v4/service?limit=3"
   ```

   Expected: HTTP 200 with a JSON array of seeded Service records.

## Running verification

```cmd
verify.cmd
```

Run it as often as needed while the Component reconciles.

## What we learned

Stage 1a applied cleanly and reconciled. The Component reached
`DEPLOYMENT_STATUS: Complete`, three ExposedAPIs were created, three Istio
VirtualServices were created, and all three TMF APIs returned HTTP 200
through the ingress with real seeded data. The observations below are the
real deliverable - they directly inform Stage 1b (`tmf-odac-mock`).

### 1. Namespace must match `COMPONENT_NAMESPACE`

The Canvas Helm chart ships `component-operator` configured to watch only
`components,odacompns-*` (see configmap `canvas/component-operator-configmap`).
Our first attempt used a singular `component` namespace; the operator
started cleanly, logged `Monitoring namespace components,odacompns-*`, and
then did nothing - it literally could not see our Component CRD. Fix is to
name the namespace `components` (plural). This is the single most important
operational fact for Stage 1b.

### 2. The component-gateway is HTTPS-only

Plain HTTP to the Istio ingress returns 404. The ExposedAPI status URL
reports `https://`, which is correct - trust it. Curl needs `-k` against
the self-signed certificate in MiniKube.

### 3. v1 CRD schema differs from older tutorials

The dry-run rejected fields that older blogs/tutorials still use:

| Older field          | v1 field           |
|---|---|
| `apitype`            | `apiType`          |
| `controllerRole`     | `canvasSystemRole` |
| `specification: <string>` | `specification: [{url, version}]` |

`kubectl explain component.spec.coreFunction.exposedAPIs --api-version=oda.tmforum.org/v1`
is the authoritative source - check it before writing a Component YAML.

### 4. ExposedAPI names get a version suffix

We declared `serviceinventory`; the operator created
`tmf-devkit-mock-serviceinventory-v4`. The version suffix comes from the
declared spec version. Worth knowing when writing tooling that references
ExposedAPIs by name.

### 5. Missing TMF669 is non-fatal

`identityconfig-operator-keycloak` created an `IdentityConfig` with
`IDENTITY_PROVIDER: Keycloak` and `LISTENER-REGISTERED: false`, then
allowed the Component to reach `Complete`. So implementing TMF669 in Stage
1b would *add* a registered listener at Keycloak - its absence is not a
blocker for the rest of the operator chain.

### 6. `canvas-depapi-op` is a no-op with empty `dependentAPIs`

No `DependentAPI` resources created, no error events. Confirmed.

### 7. End-to-end reconciliation: ~30 seconds

Image pull dominates (~25s for the 62MB image on a fresh node). Once the
pod is Ready, the operator chain (ExposedAPI -> VirtualService) completes
in about 5 seconds.

### 8. Stock `mchavan23/tmf-mock:0.1.1` runs cleanly in Canvas

No image rebuild needed. The container ran with `readOnlyRootFilesystem:
true`, `runAsNonRoot: true`, `runAsUser: 1000`, and an Istio sidecar
alongside it. No code or Dockerfile changes were required to land it as
an ODA Component.

## Troubleshooting cheatsheet

```cmd
REM Pod will not become Ready
kubectl describe pod -n components -l app=tmf-mock
kubectl logs -n components -l app=tmf-mock

REM Component stuck - read operator logs
kubectl logs -n canvas -l app.kubernetes.io/name=component-operator --tail=200
kubectl logs -n canvas -l app.kubernetes.io/name=api-operator-istio --tail=200
kubectl logs -n canvas -l app.kubernetes.io/name=identityconfig-operator --tail=200

REM No ExposedAPI CRDs appearing
kubectl get crd | findstr oda.tmforum
kubectl get exposedapis -A

REM No VirtualService - Istio side
kubectl get virtualservices -A
kubectl get gateway -A

REM Webhook rejected the apply - schema mismatch
kubectl logs -n canvas -l app.kubernetes.io/name=compcrdwebhook --tail=200
```

## Clean teardown

```cmd
REM Delete Component first so operators clean up ExposedAPIs/VirtualServices.
kubectl delete -f 20-component.yaml
kubectl delete -f 11-service.yaml
kubectl delete -f 10-deployment.yaml
kubectl delete -f 00-namespace.yaml
```

Confirm no orphans:

```cmd
kubectl get exposedapis -A
kubectl get virtualservices -A | findstr tmf-mock
```

Both should be empty (with respect to tmf-mock).

## What this is NOT

- **Not a Helm chart.** Stage 1b (`tmf-odac-mock`) will be Helm-based with
  proper templating. Stage 1a uses raw kubectl apply to keep the surface
  area minimal.
- **Not a conformant ODAC.** Real ODA Components implement TMF669, expose
  `/metrics`, and have a real management function. Stage 1a deliberately
  stops short.
- **Not production-ready.** Single replica, no PDB, no NetworkPolicies,
  no HPA. Learning artifact.
