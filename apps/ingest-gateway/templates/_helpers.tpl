{{- define "ingestion-gateway.name" -}}
{{ .Chart.Name }}
{{- end }}

{{- define "ingestion-gateway.fullname" -}}
{{ .Release.Name }}-{{ .Chart.Name }}
{{- end }}

{{- define "ingestion-gateway.labels" -}}
app.kubernetes.io/name: {{ include "ingestion-gateway.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion }}
{{- end }}
