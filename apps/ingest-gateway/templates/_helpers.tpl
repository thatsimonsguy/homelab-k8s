{{- define "ingest-gateway.name" -}}
{{ .Chart.Name }}
{{- end }}

{{- define "ingest-gateway.fullname" -}}
{{ .Release.Name }}
{{- end }}

{{- define "ingest-gateway.labels" -}}
app.kubernetes.io/name: {{ include "ingest-gateway.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion }}
{{- end }}
