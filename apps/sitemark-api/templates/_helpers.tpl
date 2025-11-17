{{- define "sitemark-api.name" -}}
{{ .Chart.Name }}
{{- end }}

{{- define "sitemark-api.fullname" -}}
{{ .Release.Name }}
{{- end }}

{{- define "sitemark-api.labels" -}}
app.kubernetes.io/name: {{ include "sitemark-api.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion }}
{{- end }}
