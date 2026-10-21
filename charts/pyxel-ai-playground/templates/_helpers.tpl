{{- define "pyxel.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "pyxel.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{- define "pyxel.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "pyxel.backendName" -}}
{{- printf "%s-backend" (include "pyxel.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "pyxel.frontendName" -}}
{{- printf "%s-frontend" (include "pyxel.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "pyxel.labels" -}}
helm.sh/chart: {{ include "pyxel.chart" . }}
app.kubernetes.io/name: {{ include "pyxel.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/* Selector labels; call with (dict "ctx" $ "component" "backend") */}}
{{- define "pyxel.selectorLabels" -}}
app.kubernetes.io/name: {{ include "pyxel.name" .ctx }}
app.kubernetes.io/instance: {{ .ctx.Release.Name }}
app.kubernetes.io/component: {{ .component }}
{{- end }}

{{- define "pyxel.secretName" -}}
{{- include "pyxel.fullname" . }}
{{- end }}

{{- define "pyxel.openaiSecretName" -}}
{{- if .Values.openai.existingSecret }}{{ .Values.openai.existingSecret }}{{ else }}{{ include "pyxel.secretName" . }}{{ end }}
{{- end }}

{{- define "pyxel.oauthSecretName" -}}
{{- if .Values.oauth2Proxy.existingSecret }}{{ .Values.oauth2Proxy.existingSecret }}{{ else }}{{ include "pyxel.secretName" . }}{{ end }}
{{- end }}

{{/* Whether the chart renders its own Secret */}}
{{- define "pyxel.renderSecret" -}}
{{- if or (not .Values.openai.existingSecret) (and .Values.auth.enabled (not .Values.oauth2Proxy.existingSecret)) }}true{{ end }}
{{- end }}

{{- define "pyxel.pvcName" -}}
{{- if .Values.persistence.existingClaim }}{{ .Values.persistence.existingClaim }}{{ else }}{{ printf "%s-games" (include "pyxel.fullname" .) }}{{ end }}
{{- end }}

{{- define "pyxel.redirectUrl" -}}
{{- if .Values.oauth2Proxy.redirectUrl }}{{ .Values.oauth2Proxy.redirectUrl }}
{{- else }}{{ printf "https://%s/oauth2/callback" (required "ingress.host (or oauth2Proxy.redirectUrl) is required when auth.enabled=true" .Values.ingress.host) }}
{{- end }}
{{- end }}
