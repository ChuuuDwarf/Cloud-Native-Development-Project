#!/usr/bin/env bash
# =============================================================================
# provision.sh — 從零重建 LIMS 的 GCP + k3s 環境
# =============================================================================
#
# 用途：把這次 demo 環境的「VM 層」+「k3s 層」全部用指令記錄下來，
#       VM 不見了 / 要開第二套環境時，跑這個就能重建。
#
# 前置：
#   1. 本機已裝 gcloud CLI 並 `gcloud auth login`
#   2. 已建立 GCP 專案、開啟 billing
#   3. 已切到目標專案：gcloud config set project lims-497613
#
# 用法：
#   bash deploy/k3s/provision.sh           # 全部跑
#   bash deploy/k3s/provision.sh phase1    # 只跑 phase1（見下方）
#
# 這個腳本「在本機跑」，會自己 SSH 進 VM 跑 VM 那邊該做的事。
# 大部分指令是冪等的（重複跑不會壞），少數會報 "already exists"，無視即可。
#
# 環境：寫於 2026-05-29，對應 Phase 3 完成的那次部署。
# =============================================================================

set -euo pipefail

# ---- 可調參數（之後想改機型 / region 改這裡） --------------------------------
PROJECT_ID="lims-497613"
REGION="asia-east1"
ZONE="asia-east1-b"
VM_NAME="lims"
VM_MACHINE_TYPE="e2-standard-2"          # 2 vCPU / 8GB RAM
VM_IMAGE_FAMILY="ubuntu-2204-lts"
VM_IMAGE_PROJECT="ubuntu-os-cloud"
VM_DISK_SIZE="30GB"
STATIC_IP_NAME="lims-ip"
FIREWALL_NAME="lims-allow-http"
NETWORK_TAG="lims-http"
AR_REPO_NAME="lims"                       # Artifact Registry repo
SSH_USER="user"

K3S_VERSION="v1.35.5+k3s1"
CERT_MANAGER_VERSION="v1.16.2"
ARGOCD_VERSION="v2.13.1"

PHASE="${1:-all}"

# ---- helper -----------------------------------------------------------------
log()  { echo -e "\n\033[1;36m[provision]\033[0m $*"; }
ok()   { echo -e "\033[1;32m  ✓\033[0m $*"; }
skip() { echo -e "\033[1;33m  ⊘\033[0m $*（已存在，跳過）"; }

# 在 VM 上跑指令（用 base64 包起來避免 Windows / PowerShell 跳脫地獄）
ssh_run() {
  local script_b64
  script_b64=$(echo "$1" | base64 -w0 2>/dev/null || echo "$1" | base64)
  gcloud compute ssh "${SSH_USER}@${VM_NAME}" --zone="${ZONE}" --quiet \
    --command="echo '${script_b64}' | base64 -d | sudo bash"
}

# =============================================================================
# Phase 1：GCP 基礎建設（靜態 IP、防火牆、Artifact Registry）
# =============================================================================
phase1_gcp_infra() {
  log "Phase 1：開 GCP 基礎建設"

  # 啟用必要的 API（冪等）
  gcloud services enable \
    compute.googleapis.com \
    artifactregistry.googleapis.com \
    logging.googleapis.com \
    monitoring.googleapis.com \
    --project="${PROJECT_ID}"
  ok "API 已啟用"

  # 靜態 IP
  if gcloud compute addresses describe "${STATIC_IP_NAME}" --region="${REGION}" >/dev/null 2>&1; then
    skip "靜態 IP ${STATIC_IP_NAME}"
  else
    gcloud compute addresses create "${STATIC_IP_NAME}" --region="${REGION}"
    ok "建立靜態 IP ${STATIC_IP_NAME}"
  fi
  STATIC_IP=$(gcloud compute addresses describe "${STATIC_IP_NAME}" --region="${REGION}" --format='value(address)')
  ok "靜態 IP = ${STATIC_IP}"

  # 防火牆（開 80/443）
  if gcloud compute firewall-rules describe "${FIREWALL_NAME}" >/dev/null 2>&1; then
    skip "防火牆 ${FIREWALL_NAME}"
  else
    gcloud compute firewall-rules create "${FIREWALL_NAME}" \
      --allow="tcp:80,tcp:443" \
      --target-tags="${NETWORK_TAG}" \
      --source-ranges="0.0.0.0/0" \
      --description="LIMS 對外 HTTP/HTTPS"
    ok "建立防火牆 ${FIREWALL_NAME}"
  fi

  # Artifact Registry
  if gcloud artifacts repositories describe "${AR_REPO_NAME}" --location="${REGION}" >/dev/null 2>&1; then
    skip "Artifact Registry ${AR_REPO_NAME}"
  else
    gcloud artifacts repositories create "${AR_REPO_NAME}" \
      --repository-format=docker \
      --location="${REGION}" \
      --description="LIMS docker images"
    ok "建立 Artifact Registry ${AR_REPO_NAME}"
  fi
}

# =============================================================================
# Phase 2：開 VM
# =============================================================================
phase2_vm() {
  log "Phase 2：開 VM ${VM_NAME}"

  if gcloud compute instances describe "${VM_NAME}" --zone="${ZONE}" >/dev/null 2>&1; then
    skip "VM ${VM_NAME}"
    return
  fi

  gcloud compute instances create "${VM_NAME}" \
    --zone="${ZONE}" \
    --machine-type="${VM_MACHINE_TYPE}" \
    --image-family="${VM_IMAGE_FAMILY}" \
    --image-project="${VM_IMAGE_PROJECT}" \
    --boot-disk-size="${VM_DISK_SIZE}" \
    --address="${STATIC_IP_NAME}" \
    --tags="${NETWORK_TAG}" \
    --scopes="cloud-platform"   # 讓 VM 用 metadata token 拉 Artifact Registry / 寫 logging
  ok "VM 已建立"

  log "等 30 秒讓 SSH 就緒..."
  sleep 30
}

# =============================================================================
# Phase 3：給 VM 的 service account 開權限
# =============================================================================
phase3_iam() {
  log "Phase 3：給 VM service account 開 IAM 權限"

  VM_SA=$(gcloud compute instances describe "${VM_NAME}" --zone="${ZONE}" \
    --format='value(serviceAccounts[0].email)')
  ok "VM SA = ${VM_SA}"

  for role in \
    "roles/artifactregistry.reader" \
    "roles/logging.logWriter" \
    "roles/monitoring.metricWriter"; do
    gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
      --member="serviceAccount:${VM_SA}" \
      --role="${role}" \
      --condition=None >/dev/null
    ok "授予 ${role}"
  done
}

# =============================================================================
# Phase 4：在 VM 上裝 k3s
# =============================================================================
phase4_k3s() {
  log "Phase 4：在 VM 上裝 k3s ${K3S_VERSION}"

  ssh_run "
    set -e
    if systemctl is-active --quiet k3s; then
      echo '  k3s 已在跑，跳過安裝'
    else
      curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION='${K3S_VERSION}' sh -
      systemctl enable k3s
    fi
    # 等 node 就緒
    until kubectl get nodes 2>/dev/null | grep -q ' Ready'; do
      echo '  等 node Ready...'
      sleep 3
    done
    kubectl get nodes
  "
  ok "k3s 已就緒"
}

# =============================================================================
# Phase 5：在 VM 上裝 cert-manager（給 HTTPS 用）
# =============================================================================
phase5_cert_manager() {
  log "Phase 5：裝 cert-manager ${CERT_MANAGER_VERSION}"

  ssh_run "
    set -e
    if kubectl get ns cert-manager >/dev/null 2>&1; then
      echo '  cert-manager 已裝，跳過'
    else
      kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/${CERT_MANAGER_VERSION}/cert-manager.yaml
      echo '  等 cert-manager 就緒...'
      kubectl -n cert-manager wait --for=condition=Available deployment --all --timeout=300s
    fi
  "
  ok "cert-manager 已就緒"
}

# =============================================================================
# Phase 6：把 repo 裡的 observability manifests 套上去
# =============================================================================
phase6_observability() {
  log "Phase 6：套用 observability（logging + monitoring + clusterissuers）"

  # 把本機的 yaml 用 base64 塞進 VM 再 apply（避開 Windows scp 問題）
  for f in \
    "deploy/k3s/observability/cert-manager/clusterissuers.yaml" \
    "deploy/k3s/observability/logging/fluent-bit.yaml" \
    "deploy/k3s/observability/monitoring/kube-state-metrics.yaml" \
    "deploy/k3s/observability/ar-token-refresher.yaml"; do
    if [[ ! -f "$f" ]]; then
      echo "  ⚠️  找不到 $f，跳過"
      continue
    fi
    content_b64=$(base64 -w0 "$f" 2>/dev/null || base64 "$f")
    ssh_run "echo '${content_b64}' | base64 -d | kubectl apply -f -"
    ok "套用 $f"
  done
}

# =============================================================================
# Phase 7：在 VM 上裝 Google Ops Agent（host 端 metrics → Cloud Monitoring）
# =============================================================================
phase7_ops_agent() {
  log "Phase 7：裝 Google Ops Agent"

  ssh_run "
    set -e
    if systemctl is-active --quiet google-cloud-ops-agent; then
      echo '  Ops Agent 已在跑，跳過安裝'
    else
      # 加 GCP apt repo
      curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg \
        | gpg --dearmor -o /etc/apt/keyrings/cloud.google.gpg
      echo 'deb [signed-by=/etc/apt/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt google-cloud-ops-agent-jammy-all main' \
        > /etc/apt/sources.list.d/google-cloud-ops-agent.list
      apt-get update
      apt-get install -y google-cloud-ops-agent
    fi

    # 設定：抓 kube-state-metrics 的 NodePort 30808
    cat > /etc/google-cloud-ops-agent/config.yaml <<'EOF'
metrics:
  receivers:
    kube_state:
      type: prometheus
      config:
        scrape_configs:
          - job_name: 'kube-state-metrics'
            scrape_interval: 60s
            static_configs:
              - targets: ['localhost:30808']
  service:
    pipelines:
      kube_state_pipeline:
        receivers: [kube_state]
EOF
    systemctl restart google-cloud-ops-agent
  "
  ok "Ops Agent 已就緒"
}

# =============================================================================
# Phase 8：建立 namespaces（lims-prod / lims-staging）
# =============================================================================
phase8_namespaces() {
  log "Phase 8：建立 lims-prod / lims-staging namespaces"
  ssh_run "
    kubectl create namespace lims-prod --dry-run=client -o yaml | kubectl apply -f -
    kubectl create namespace lims-staging --dry-run=client -o yaml | kubectl apply -f -
  "
  ok "namespaces OK"
}

# =============================================================================
# 提示：secret 不在這裡建，要手動跑（避免任何形式存進 repo / 腳本歷史）
# =============================================================================
print_secret_reminder() {
  cat <<EOF

================================================================================
  ⚠️  下一步：在 VM 上建立 lims-secrets（這個腳本「不會」幫你做）
================================================================================

  原因：避免真實密碼出現在腳本、shell history、或 CI log 裡。

  SSH 進 VM：
    gcloud compute ssh ${SSH_USER}@${VM_NAME} --zone=${ZONE}

  然後在 VM 上跑：
    JWT_SECRET=\$(openssl rand -hex 32)
    PG_PASS=\$(openssl rand -hex 16)

    sudo kubectl -n lims-prod create secret generic lims-secrets \\
      --from-literal=JWT_SECRET=\$JWT_SECRET \\
      --from-literal=POSTGRES_PASSWORD=\$PG_PASS \\
      --from-literal=DATABASE_URL="postgresql+asyncpg://lims:\${PG_PASS}@postgres:5432/lims"

    # staging 也來一份（密碼可以一樣或不一樣，看你）
    sudo kubectl -n lims-staging create secret generic lims-secrets ...

================================================================================
EOF
}

# =============================================================================
# Phase 9：裝 ArgoCD（GitOps controller，pull-based 自動同步）
# =============================================================================
phase9_argocd() {
  log "Phase 9：裝 ArgoCD ${ARGOCD_VERSION}"

  ssh_run "
    set -e
    if kubectl get ns argocd >/dev/null 2>&1; then
      echo '  argocd namespace 已存在，跳過安裝（要升級請手動）'
    else
      kubectl create namespace argocd
      kubectl apply -n argocd \
        -f https://raw.githubusercontent.com/argoproj/argo-cd/${ARGOCD_VERSION}/manifests/install.yaml
      echo '  等 ArgoCD server 就緒...'
      kubectl -n argocd wait --for=condition=Available deployment --all --timeout=300s
    fi
  "
  ok "ArgoCD 已就緒"

  # 套用 Application（指向 repo 的 overlays/staging、overlays/prod）
  for f in \
    'deploy/argocd/applications/lims-staging.yaml' \
    'deploy/argocd/applications/lims-prod.yaml'; do
    if [[ ! -f \"\$f\" ]]; then
      echo \"  ⚠️  找不到 \$f，跳過\"
      continue
    fi
    content_b64=\$(base64 -w0 \"\$f\" 2>/dev/null || base64 \"\$f\")
    ssh_run \"echo '\${content_b64}' | base64 -d | kubectl apply -f -\"
    ok \"套用 \$f\"
  done

  # 印 admin 密碼（首次安裝才有意義；之後可手動改）
  ssh_run "
    if kubectl -n argocd get secret argocd-initial-admin-secret >/dev/null 2>&1; then
      echo
      echo '  ⚠️  ArgoCD 初始 admin 密碼（請改掉並刪掉這個 secret）：'
      kubectl -n argocd get secret argocd-initial-admin-secret \
        -o jsonpath='{.data.password}' | base64 -d
      echo
    fi
  "
}

# =============================================================================
# 主流程
# =============================================================================
case "${PHASE}" in
  phase1) phase1_gcp_infra ;;
  phase2) phase2_vm ;;
  phase3) phase3_iam ;;
  phase4) phase4_k3s ;;
  phase5) phase5_cert_manager ;;
  phase6) phase6_observability ;;
  phase7) phase7_ops_agent ;;
  phase8) phase8_namespaces ;;
  phase9) phase9_argocd ;;
  all)
    phase1_gcp_infra
    phase2_vm
    phase3_iam
    phase4_k3s
    phase5_cert_manager
    phase6_observability
    phase7_ops_agent
    phase8_namespaces
    phase9_argocd
    print_secret_reminder
    ;;
  *)
    echo "用法：bash $0 [all|phase1|phase2|...|phase9]"
    exit 1
    ;;
esac

log "完成 ✓"


GCP_PROJECT_ID    = lims-497613
GCP_WIF_PROVIDER  = projects/700315573384/locations/global/workloadIdentityPools/github-pool/providers/github-provider
GCP_SA_EMAIL      = github-actions-ci@lims-497613.iam.gserviceaccount.com
GCP_REGION        = asia-east1
GCP_AR_REPO       = lims