{{- define "sitemark.name" -}}
{{ .Chart.Name }}
{{- end }}

{{- define "sitemark.fullname" -}}
{{ .Release.Name }}
{{- end }}

{{- define "sitemark.labels" -}}
app.kubernetes.io/name: {{ include "sitemark.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion }}
{{- end }}