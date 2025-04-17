{{- define "embedding-service.name" -}}
{{ .Chart.Name }}
{{- end }}

{{- define "embedding-service.fullname" -}}
{{ .Release.Name }}
{{- end }}

{{- define "embedding-service.labels" -}}
app.kubernetes.io/name: {{ include "embedding-service.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion }}
{{- end }}
