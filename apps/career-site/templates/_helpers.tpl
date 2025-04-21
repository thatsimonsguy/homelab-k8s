{{- define "career-site.name" -}}
{{ .Chart.Name }}
{{- end }}

{{- define "career-site.fullname" -}}
{{ .Release.Name }}
{{- end }}

{{- define "career-site.labels" -}}
app.kubernetes.io/name: {{ include "career-site.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion }}
{{- end }}
