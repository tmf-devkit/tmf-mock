@echo off
REM ----------------------------------------------------------------------
REM Stage 1a verification - run after `kubectl apply -f .`
REM Read-only. Safe to re-run as needed.
REM ----------------------------------------------------------------------
setlocal
set NS=components
set COMP=tmf-devkit-mock

echo.
echo === 1. Cluster sanity ===
kubectl get nodes
kubectl get ns %NS%

echo.
echo === 2. Pod ===
kubectl get pods -n %NS% -l app=tmf-mock -o wide
kubectl get events -n %NS% --sort-by=.lastTimestamp ^| findstr /I "tmf-mock"

echo.
echo === 3. Service ===
kubectl get svc -n %NS% tmf-mock-svc -o wide

echo.
echo === 4. ODA Component ===
kubectl get component -n %NS% %COMP%
kubectl get component -n %NS% %COMP% -o yaml

echo.
echo === 5. ExposedAPI CRDs ===
kubectl get exposedapis -n %NS% -l oda.tmforum.org/componentName=%COMP%

echo.
echo === 6. Istio VirtualServices ===
kubectl get virtualservices -n %NS%
kubectl get virtualservices -A ^| findstr /I "tmf-mock tmf-devkit"

echo.
echo === 7. IdentityConfig ===
kubectl get identityconfigs -n %NS% -l oda.tmforum.org/componentName=%COMP% 2^>nul

echo.
echo === 8. Istio ingress ===
kubectl get svc -n istio-ingress istio-ingress -o wide

echo.
echo === 9. Smoke test ===
for /f "tokens=*" %%i in ('kubectl get svc -n istio-ingress istio-ingress -o jsonpath^="{.status.loadBalancer.ingress[0].ip}"') do set INGRESS=%%i
if "%INGRESS%"=="" (
    echo No ingress IP. Is minikube tunnel running?
) else (
    echo Ingress IP: %INGRESS%
    curl -sS -m 10 -o NUL -w "HTTP %%{http_code} time=%%{time_total}s\n" "http://%INGRESS%/tmf-api/serviceInventoryManagement/v4/service?limit=3"
)

echo.
echo === If not Ready, capture operator logs: ===
echo   kubectl logs -n canvas -l app.kubernetes.io/name=component-operator
echo   kubectl logs -n canvas -l app.kubernetes.io/name=api-operator-istio
echo   kubectl logs -n canvas -l app.kubernetes.io/name=identityconfig-operator
endlocal
