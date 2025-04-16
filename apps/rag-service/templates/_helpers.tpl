{{- define "rag-service.name" -}}
{{ .Chart.Name }}
{{- end }}

{{- define "rag-service.fullname" -}}
{{ .Release.Name }}
{{- end }}

{{- define "rag-service.labels" -}}
app.kubernetes.io/name: {{ include "rag-service.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion }}
{{- end }}
