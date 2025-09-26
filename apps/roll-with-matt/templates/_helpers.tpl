{{- define "roll-with-matt.name" -}}
{{ .Chart.Name }}
{{- end }}

{{- define "roll-with-matt.fullname" -}}
{{ .Release.Name }}
{{- end }}

{{- define "roll-with-matt.labels" -}}
app.kubernetes.io/name: {{ include "roll-with-matt.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion }}
{{- end }}