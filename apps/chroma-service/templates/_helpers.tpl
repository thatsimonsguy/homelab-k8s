{{- define "chroma-service.name" -}}
{{ .Chart.Name }}
{{- end }}

{{- define "chroma-service.fullname" -}}
{{ .Release.Name }}
{{- end }}

{{- define "chroma-service.labels" -}}
app.kubernetes.io/name: {{ include "chroma-service.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion }}
{{- end }}
