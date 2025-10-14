{{- define "bright-badger-site.name" -}}
{{ .Chart.Name }}
{{- end }}

{{- define "bright-badger-site.fullname" -}}
{{ .Release.Name }}
{{- end }}

{{- define "bright-badger-site.labels" -}}
app.kubernetes.io/name: {{ include "bright-badger-site.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion }}
{{- end }}