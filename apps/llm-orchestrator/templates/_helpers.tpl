{{- define "llm-orchestrator.name" -}}
{{ .Chart.Name }}
{{- end }}

{{- define "llm-orchestrator.fullname" -}}
{{ .Release.Name }}
{{- end }}

{{- define "llm-orchestrator.labels" -}}
app.kubernetes.io/name: {{ include "llm-orchestrator.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion }}
{{- end }}
