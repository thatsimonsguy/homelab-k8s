{{- define "qdrant.name" -}}
{{ .Chart.Name }}
{{- end }}

{{- define "qdrant.fullname" -}}
{{ .Release.Name }}
{{- end }}

{{- define "qdrant.labels" -}}
app.kubernetes.io/name: {{ include "qdrant.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion }}
{{- end }}
